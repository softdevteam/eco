
package jcifs.smb;

import java.net.URLConnection;
import java.net.URL;
import java.net.MalformedURLException;
import java.net.UnknownHostException;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.security.Principal;
import jcifs.Config;
import jcifs.util.LogStream;
import jcifs.UniAddress;
import jcifs.netbios.NbtAddress;

import java.util.Date;


public class SmbFile extends URLConnection {

    // these are shifted for use in flags
    static final int O_RDONLY = 0x010000;
    static final int O_WRONLY = 0x020000;
    static final int O_RDWR   = 0x030000;
    static final int O_APPEND = 0x040000;

    // share access
    public static final int FILE_NO_SHARE     = 0x00;
    public static final int FILE_SHARE_READ   = 0x01;
    public static final int FILE_SHARE_WRITE  = 0x02;
    public static final int FILE_SHARE_DELETE = 0x04;

    // Open Function Encoding
    // create if the file does not exist
    static final int O_CREAT  = 0x0010;
    // fail if the file exists
    static final int O_EXCL   = 0x0001;
    // truncate if the file exists
    static final int O_TRUNC  = 0x0002;

    // file attribute encoding
    public static final int ATTR_READONLY   = 0x01;
    public static final int ATTR_HIDDEN     = 0x02;
    public static final int ATTR_SYSTEM     = 0x04;
    public static final int ATTR_VOLUME     = 0x08;
    public static final int ATTR_DIRECTORY  = 0x10;
    public static final int ATTR_ARCHIVE    = 0x20;

    // extended file attribute encoding(others same as above)
    static final int ATTR_COMPRESSED       = 0x800;
    static final int ATTR_NORMAL           = 0x080;
    static final int ATTR_TEMPORARY        = 0x100;

    static final int ATTR_GET_MASK = 0x7FFF;
    static final int ATTR_SET_MASK = 0x30A7;

    static final int DEFAULT_ATTR_EXPIRATION_PERIOD = 5000;

    static final int HASH_DOT     = ".".hashCode();
    static final int HASH_DOT_DOT = "..".hashCode();

    static LogStream log = LogStream.getInstance();
    static long attrExpirationPeriod;

    static {
        try {
            Class.forName( "jcifs.Config" );
        } catch( ClassNotFoundException cnfe ) {
            cnfe.printStackTrace();
        }
        attrExpirationPeriod = Config.getLong( "jcifs.smb.client.attrExpirationPeriod", DEFAULT_ATTR_EXPIRATION_PERIOD );
    }

    public static final int TYPE_FILESYSTEM = 0x01;
    public static final int TYPE_WORKGROUP = 0x02;
    public static final int TYPE_SERVER = 0x04;
    public static final int TYPE_SHARE = 0x08;
    public static final int TYPE_NAMED_PIPE = 0x10;
    public static final int TYPE_PRINTER = 0x20;
    public static final int TYPE_COMM = 0x40;


    private String canon;            // Initially null; set by getUncPath; dir must end with '/'
    private String share;            // Can be null
    private long createTime;
    private long lastModified;
    private int attributes;
    private long attrExpiration;
    private long size;
    private long sizeExpiration;
    private NtlmPasswordAuthentication auth; // Cannot be null
    private boolean isExists;
    private int shareAccess = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE;
    private SmbComBlankResponse blank_resp = null;
    private DfsReferral dfsReferral = null;  // Only used by getDfsPath()

    SmbTree tree = null;             // Initially null; may be !tree.treeConnected
    String unc;                      // Initially null; set by getUncPath; never ends with '/'
    int fid;                         // Initially 0; set by open()
    int type;
    boolean opened;
    int tree_num;

    public SmbFile( String url ) throws MalformedURLException {
        this( new URL( null, url, Handler.SMB_HANDLER ));
    }

    public SmbFile( SmbFile context, String name )
                throws MalformedURLException, UnknownHostException {
        this( context.isWorkgroup0() ?
            new URL( null, "smb://" + name, Handler.SMB_HANDLER ) :
            new URL( context.url, name, Handler.SMB_HANDLER ), context.auth );
    }


    public SmbFile( String context, String name ) throws MalformedURLException {
        this( new URL( new URL( null, context, Handler.SMB_HANDLER ),
                name, Handler.SMB_HANDLER ));
    }

    public SmbFile( String url, NtlmPasswordAuthentication auth )
                    throws MalformedURLException {
        this( new URL( null, url, Handler.SMB_HANDLER ), auth );
    }
    public SmbFile( String url, NtlmPasswordAuthentication auth, int shareAccess )
                    throws MalformedURLException {
        this( new URL( null, url, Handler.SMB_HANDLER ), auth );
        if ((shareAccess & ~(FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE)) != 0) {
            throw new RuntimeException( "Illegal shareAccess parameter" );
        }
        this.shareAccess = shareAccess;
    }
    public SmbFile( String context, String name, NtlmPasswordAuthentication auth )
                    throws MalformedURLException {
        this( new URL( new URL( null, context, Handler.SMB_HANDLER ), name, Handler.SMB_HANDLER ), auth );
    }
    public SmbFile( String context, String name, NtlmPasswordAuthentication auth, int shareAccess )
                    throws MalformedURLException {
        this( new URL( new URL( null, context, Handler.SMB_HANDLER ), name, Handler.SMB_HANDLER ), auth );
        if ((shareAccess & ~(FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE)) != 0) {
            throw new RuntimeException( "Illegal shareAccess parameter" );
        }
        this.shareAccess = shareAccess;
    }
    public SmbFile( SmbFile context, String name, int shareAccess )
                    throws MalformedURLException, UnknownHostException {
        this( context.isWorkgroup0() ?
            new URL( null, "smb://" + name, Handler.SMB_HANDLER ) :
            new URL( context.url, name, Handler.SMB_HANDLER ), context.auth );
        if ((shareAccess & ~(FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE)) != 0) {
            throw new RuntimeException( "Illegal shareAccess parameter" );
        }
        this.shareAccess = shareAccess;
    }
    public SmbFile( URL url ) {
        this( url, new NtlmPasswordAuthentication( url.getUserInfo() ));
    }
    public SmbFile( URL url, NtlmPasswordAuthentication auth ) {
        super( url );
        this.auth = auth == null ? new NtlmPasswordAuthentication( url.getUserInfo() ) : auth;

        getUncPath0();
    }
    SmbFile( SmbFile context, String name, int type,
                int attributes, long createTime, long lastModified, long size )
                throws MalformedURLException, UnknownHostException {
        this( context.isWorkgroup0() ?
            new URL( null, "smb://" + name + "/", Handler.SMB_HANDLER ) :
            new URL( context.url, name + (( attributes & ATTR_DIRECTORY ) > 0 ? "/" : "" )));


        g
        auth = context.auth;


        if( context.share != null ) {
            this.tree = context.tree;
        }
        int last = name.length() - 1;
        if( name.charAt( last ) == '/' ) {
            name = name.substring( 0, last );
        }
        if( context.share == null ) {
            this.unc = "\\";
        } else if( context.unc.equals( "\\" )) {
            this.unc = '\\' + name;
        } else {
            this.unc = context.unc + '\\' + name;
        }
        this.type = type;
        this.attributes = attributes;
        this.createTime = createTime;
        this.lastModified = lastModified;
        this.size = size;
        isExists = true;

        attrExpiration = sizeExpiration =
                System.currentTimeMillis() + attrExpirationPeriod;
    }

    private SmbComBlankResponse blank_resp() {
        if( blank_resp == null ) {
            blank_resp = new SmbComBlankResponse();
        }
        return blank_resp;
    }
    void send( ServerMessageBlock request,
                    ServerMessageBlock response ) throws SmbException {
        for( ;; ) {
            connect0();
            if( tree.inDfs ) {
                DfsReferral dr = tree.session.transport.lookupReferral( unc );
                if( dr != null ) {
                    UniAddress addr;
                    SmbTransport trans;

                    try {
                        addr = UniAddress.getByName( dr.server );
                    } catch( UnknownHostException uhe ) {
                        throw new SmbException( dr.server, uhe );
                    }

                    trans = SmbTransport.getSmbTransport( addr, url.getPort() );
                    tree = trans.getSmbSession( auth ).getSmbTree( dr.share, null );
                    unc = dr.nodepath + unc.substring( dr.path.length() );
                    if( request.path.charAt( request.path.length() - 1 ) == '\\' ) {
                        request.path = unc + '\\';
                    } else {
                        request.path = unc;
                    }
                    dfsReferral = dr;
                }
                request.flags2 |= ServerMessageBlock.FLAGS2_RESOLVE_PATHS_IN_DFS;
            } else {
                request.flags2 &= ~ServerMessageBlock.FLAGS2_RESOLVE_PATHS_IN_DFS;
            }
            try {
                tree.send( request, response );
                break;
            } catch( DfsReferral dr ) {
                if( dr.resolveHashes ) {
                    throw dr;
                }
                request.reset();
            }
        }
    }

    static String queryLookup( String query, String param ) {
        char in[] = query.toCharArray();
        int i, ch, st, eq;

        st = eq = 0;
        for( i = 0; i < in.length; i++) {
            ch = in[i];
            if( ch == '&' ) {
                if( eq > st ) {
                    String p = new String( in, st, eq - st );
                    if( p.equalsIgnoreCase( param )) {
                        eq++;
                        return new String( in, eq, i - eq );
                    }
                }
                st = i + 1;
            } else if( ch == '=' ) {
                eq = i;
            }
        }
        if( eq > st ) {
            String p = new String( in, st, eq - st );
            if( p.equalsIgnoreCase( param )) {
                eq++;
                return new String( in, eq, in.length - eq );
            }
        }

        return null;
    }

    UniAddress getAddress() throws UnknownHostException {
        String host = url.getHost();
        String path = url.getPath();
        String query = url.getQuery();

        if( query != null ) {
            String server = queryLookup( query, "server" );
            if( server != null && server.length() > 0 ) {
                return UniAddress.getByName( server );
            }
        }

        if( host.length() == 0 ) {
            try {
                NbtAddress addr = NbtAddress.getByName(
                        NbtAddress.MASTER_BROWSER_NAME, 0x01, null);
                return UniAddress.getByName( addr.getHostAddress() );
            } catch( UnknownHostException uhe ) {
                NtlmPasswordAuthentication.initDefaults();
                if( NtlmPasswordAuthentication.DEFAULT_DOMAIN.equals( "?" )) {
                    throw uhe;
                }
                return UniAddress.getByName( NtlmPasswordAuthentication.DEFAULT_DOMAIN, true );
            }
        } else if( path.length() == 0 || path.equals( "/" )) {
            return UniAddress.getByName( host, true );
        } else {
            return UniAddress.getByName( host );
        }
    }
    void connect0() throws SmbException {
        try {
            connect();
        } catch( UnknownHostException uhe ) {
            throw new SmbException( "Failed to connect to server", uhe );
        } catch( SmbException se ) {
            throw se;
        } catch( IOException ioe ) {
            throw new SmbException( "Failed to connect to server", ioe );
        }
    }
    public void connect() throws IOException {
        SmbTransport trans;
        SmbSession ssn;
        UniAddress addr;

        if( isConnected() ) {
            return;
        }

        getUncPath0();
        addr = getAddress();

        trans = SmbTransport.getSmbTransport( addr, url.getPort() );
        ssn = trans.getSmbSession( auth );
        tree = ssn.getSmbTree( share, null );

        try {
            tree.treeConnect( null, null );
        } catch( SmbAuthException sae ) {
            NtlmPasswordAuthentication a;

            if( share == null ) { // IPC$ - try "anonymous" credentials
                ssn = trans.getSmbSession( NtlmPasswordAuthentication.NULL );
                tree = ssn.getSmbTree( null, null );
                tree.treeConnect( null, null );
            } else if(( a = NtlmAuthenticator.requestNtlmPasswordAuthentication(
                        url.toString(), sae )) != null ) {
                auth = a;
                ssn = trans.getSmbSession( auth );
                tree = ssn.getSmbTree( share, null );
                tree.treeConnect( null, null );
            } else {
                throw sae;
            }
        }
    }
    boolean isConnected() {
        return (connected = tree != null && tree.treeConnected);
    }
    int open0( int flags, int attrs, int options ) throws SmbException {
        int f;

        connect0();

        if( log.level > 2 )
            log.println( "open0: " + unc );

 
        if( tree.session.transport.hasCapability( ServerMessageBlock.CAP_NT_SMBS )) {
            SmbComNTCreateAndXResponse response = new SmbComNTCreateAndXResponse();
            send( new SmbComNTCreateAndX( unc, flags, shareAccess,
                    attrs, options, null ), response );
            f = response.fid;
            attributes = response.extFileAttributes & ATTR_GET_MASK;
            attrExpiration = System.currentTimeMillis() + attrExpirationPeriod;
            isExists = true;
        } else {
            SmbComOpenAndXResponse response = new SmbComOpenAndXResponse();
            send( new SmbComOpenAndX( unc, flags, null ), response );
            f = response.fid;
        }

        return f;
    }
    void open( int flags, int attrs, int options ) throws SmbException {
        if( isOpen() ) {
            return;
        }
        fid = open0( flags, attrs, options );
        opened = true;
        tree_num = tree.tree_num;
    }
    boolean isOpen() {
        return opened && isConnected() && tree_num == tree.tree_num;
    }
    void close( int f, long lastWriteTime ) throws SmbException {

        if( log.level > 2 )
            log.println( "close: " + f );

        send( new SmbComClose( f, lastWriteTime ), blank_resp() );
    }
    void close( long lastWriteTime ) throws SmbException {
        if( isOpen() == false ) {
            return;
        }
        close( fid, lastWriteTime );
        opened = false;
    }
    void close() throws SmbException {
        close( 0L );
    }


    public Principal getPrincipal() {
        return auth;
    }


    public String getName() {
        getUncPath0();
        if( canon.length() > 1 ) {
            int i = canon.length() - 2;
            while( canon.charAt( i ) != '/' ) {
                i--;
            }
            return canon.substring( i + 1 );
        } else if( share != null ) {
            return share + '/';
        } else if( url.getHost().length() > 0 ) {
            return url.getHost() + '/';
        } else {
            return "smb://";
        }
    }


    public String getParent() {
        String str = url.getAuthority();

        if( str.length() > 0 ) {
            StringBuffer sb = new StringBuffer( "smb://" );

            sb.append( str );

            getUncPath0();
            if( canon.length() > 1 ) {
                sb.append( canon );
            } else {
                sb.append( '/' );
            }

            str = sb.toString();

            int i = str.length() - 2;
            while( str.charAt( i ) != '/' ) {
                i--;
            }

            return str.substring( 0, i + 1 );
        }

        return "smb://";
    }


    public String getPath() {
        return url.toString();
    }

    String getUncPath0() {
        if( unc == null ) {
            char[] in = url.getPath().toCharArray();
            char[] out = new char[in.length];
            int length = in.length, i, o, state, s;

            state = 0;
            o = 0;
            for( i = 0; i < length; i++ ) {
                switch( state ) {
                    case 0:
                        if( in[i] != '/' ) {
                            return null;
                        }
                        out[o++] = in[i];
                        state = 1;
                        break;
                    case 1:
                        if( in[i] == '/' ) {
                            break;
                        } else if( in[i] == '.' &&
                                    (( i + 1 ) >= length || in[i + 1] == '/' )) {
                            i++;
                            break;
                        } else if(( i + 1 ) < length &&
                                    in[i] == '.' &&
                                    in[i + 1] == '.' &&
                                    (( i + 2 ) >= length || in[i + 2] == '/' )) {
                            i += 2;
                            if( o == 1 ) break;
                            do {
                                o--;
                            } while( o > 1 && out[o - 1] != '/' );
                            break;
                        }
                        state = 2;
                    case 2:
                        if( in[i] == '/' ) {
                            state = 1;
                        }
                        out[o++] = in[i];
                        break;
                }
            }

            canon = new String( out, 0, o );

            if( o > 1 ) {
                o--;
                i = canon.indexOf( '/', 1 );
                if( i < 0 ) {
                    share = canon.substring( 1 );
                    unc = "\\";
                } else if( i == o ) {
                    share = canon.substring( 1, i );
                    unc = "\\";
                } else {
                    share = canon.substring( 1, i );
                    unc = canon.substring( i, out[o] == '/' ? o : o + 1 );
                    unc = unc.replace( '/', '\\' );
                }
            } else {
                share = null;
                unc = "\\";
            }
        }
        return unc;
    }
    public String getUncPath() {
        getUncPath0();
        if( share == null ) {
            return "\\\\" + url.getHost();
        }
        return "\\\\" + url.getHost() + canon.replace( '/', '\\' );
    }


    public String getCanonicalPath() {
        String str = url.getAuthority();
        getUncPath0();
        if( str.length() > 0 ) {
            return "smb://" + url.getAuthority() + canon;
        }
        return "smb://";
    }


    public String getShare() {
        return share;
    }


    public String getServer() {
        String str = url.getHost();
        if( str.length() == 0 ) {
            return null;
        }
        return str;
    }

    public int getType() throws SmbException {
        if( type == 0 ) {
            if( getUncPath0().length() > 1 ) {
                type = TYPE_FILESYSTEM;
            } else if( share != null ) {
                // treeConnect good enough to test service type
                connect0();
                if( share.equals( "IPC$" )) {
                    type = TYPE_NAMED_PIPE;
                } else if( tree.service.equals( "LPT1:" )) {
                    type = TYPE_PRINTER;
                } else if( tree.service.equals( "COMM" )) {
                    type = TYPE_COMM;
                } else {
                    type = TYPE_SHARE;
                }
            } else if( url.getAuthority().length() == 0 ) {
                type = TYPE_WORKGROUP;
            } else {
                UniAddress addr;
                try {
                    addr = getAddress();
                } catch( UnknownHostException uhe ) {
                    throw new SmbException( url.toString(), uhe );
                }
                if( addr.getAddress() instanceof NbtAddress ) {
                    int code = ((NbtAddress)addr.getAddress()).getNameType();
                    if( code == 0x1d || code == 0x1b ) {
                        type = TYPE_WORKGROUP;
                        return type;
                    }
                }
                type = TYPE_SERVER;
            }
        }
        return type;
    }
    boolean isWorkgroup0() throws UnknownHostException {
        if( type == TYPE_WORKGROUP || url.getHost().length() == 0 ) {
            type = TYPE_WORKGROUP;
            return true;
        } else {
            getUncPath0();
            if( share == null ) {
                UniAddress addr = getAddress();
                if( addr.getAddress() instanceof NbtAddress ) {
                    int code = ((NbtAddress)addr.getAddress()).getNameType();
                    if( code == 0x1d || code == 0x1b ) {
                        type = TYPE_WORKGROUP;
                        return true;
                    }
                }
                type = TYPE_SERVER;
            }
        }
        return false;
    }

    Info queryPath( String path, int infoLevel ) throws SmbException {
        connect0();

        if( log.level > 2 )
            log.println( "queryPath: " + path );

        if( tree.session.transport.hasCapability( ServerMessageBlock.CAP_NT_SMBS )) {

 
            Trans2QueryPathInformationResponse response =
                    new Trans2QueryPathInformationResponse( infoLevel );
            send( new Trans2QueryPathInformation( path, infoLevel ), response );

            return response.info;
        } else {


            SmbComQueryInformationResponse response =
                    new SmbComQueryInformationResponse(
                    tree.session.transport.server.serverTimeZone * 1000 * 60L );
            send( new SmbComQueryInformation( path ), response );
            return response;
        }
    }


    public boolean exists() throws SmbException {

        if( attrExpiration > System.currentTimeMillis() ) {
            return isExists;
        }

        attributes = ATTR_READONLY | ATTR_DIRECTORY;
        createTime = 0L;
        lastModified = 0L;
        isExists = false;

        try {
            if( url.getHost().length() == 0 ) {
            } else if( share == null ) {
                if( getType() == TYPE_WORKGROUP ) {
                    UniAddress.getByName( url.getHost(), true );
                } else {
                    UniAddress.getByName( url.getHost() ).getHostName();
                }
            } else if( getUncPath0().length() == 1 ||
                                        share.equalsIgnoreCase( "IPC$" )) {
                connect0(); // treeConnect is good enough
            } else {
                Info info = queryPath( getUncPath0(),
                    Trans2QueryPathInformationResponse.SMB_QUERY_FILE_BASIC_INFO );
                attributes = info.getAttributes();
                createTime = info.getCreateTime();
                lastModified = info.getLastWriteTime();
            }

            isExists = true;

        } catch( UnknownHostException uhe ) {
        } catch( SmbException se ) {
            switch (se.getNtStatus()) {
                case NtStatus.NT_STATUS_NO_SUCH_FILE:
                case NtStatus.NT_STATUS_OBJECT_NAME_INVALID:
                case NtStatus.NT_STATUS_OBJECT_NAME_NOT_FOUND:
                case NtStatus.NT_STATUS_OBJECT_PATH_NOT_FOUND:
                    break;
                default:
                    throw se;
            }
        }

        attrExpiration = System.currentTimeMillis() + attrExpirationPeriod;

        return isExists;
    }

    public boolean canRead() throws SmbException {
        if( getType() == TYPE_NAMED_PIPE ) { // try opening the pipe for reading?
            return true;
        }
        return exists(); // try opening and catch sharing violation?
    }



    public boolean canWrite() throws SmbException {
        if( getType() == TYPE_NAMED_PIPE ) { // try opening the pipe for writing?
            return true;
        }
        return exists() && ( attributes & ATTR_READONLY ) == 0;
    }


    public boolean isDirectory() throws SmbException {
        if( getUncPath0().length() == 1 ) {
            return true;
        }
        if (!exists()) return false;
        return ( attributes & ATTR_DIRECTORY ) == ATTR_DIRECTORY;
    }


    public boolean isFile() throws SmbException {
        if( getUncPath0().length() == 1 ) {
            return false;
        }
        exists();
        return ( attributes & ATTR_DIRECTORY ) == 0;
    }


    public boolean isHidden() throws SmbException {
        if( share == null ) {
            return false;
        } else if( getUncPath0().length() == 1 ) {
            if( share.endsWith( "$" )) {
                return true;
            }
            return false;
        }
        exists();
        return ( attributes & ATTR_HIDDEN ) == ATTR_HIDDEN;
    }


    public String getDfsPath() throws SmbException {
        connect0();
        if( tree.inDfs ) {
            exists();
        }
        if( dfsReferral == null ) {
            return null;
        }
        String path = "smb:/" + (new String( dfsReferral.node + unc )).replace( '\\', '/' );
        if (isDirectory()) {
            path += '/';
        }
        return path;
    }

    public long createTime() throws SmbException {
        if( getUncPath0().length() > 1 ) {
            exists();
            return createTime;
        }
        return 0L;
    }
    public long lastModified() throws SmbException {
        if( getUncPath0().length() > 1 ) {
            exists();
            return lastModified;
        }
        return 0L;
    }
    public String[] list() throws SmbException {
        return list( "*", ATTR_DIRECTORY | ATTR_HIDDEN | ATTR_SYSTEM, null, null );
    }

    public String[] list( SmbFilenameFilter filter ) throws SmbException {
        return list( "*", ATTR_DIRECTORY | ATTR_HIDDEN | ATTR_SYSTEM, filter, null );
    }

    public SmbFile[] listFiles() throws SmbException {
        return listFiles( "*", ATTR_DIRECTORY | ATTR_HIDDEN | ATTR_SYSTEM, null, null );
    }


    public SmbFile[] listFiles( String wildcard ) throws SmbException {
        return listFiles( wildcard, ATTR_DIRECTORY | ATTR_HIDDEN | ATTR_SYSTEM, null, null );
    }
    public SmbFile[] listFiles( SmbFilenameFilter filter ) throws SmbException {
        return listFiles( "*", ATTR_DIRECTORY | ATTR_HIDDEN | ATTR_SYSTEM, filter, null );
    }
    public SmbFile[] listFiles( SmbFileFilter filter ) throws SmbException {
        return listFiles( "*", ATTR_DIRECTORY | ATTR_HIDDEN | ATTR_SYSTEM, null, filter );
    }
    String[] list( String wildcard, int searchAttributes,
                SmbFilenameFilter fnf, SmbFileFilter ff ) throws SmbException {
        ArrayList list = new ArrayList();

        try {
            if( url.getHost().length() == 0 || share == null ) {
                doNetEnum( list, false, wildcard, searchAttributes, fnf, ff );
            } else {
                doFindFirstNext( list, false, wildcard, searchAttributes, fnf, ff );
            }
        } catch( UnknownHostException uhe ) {
            throw new SmbException( url.toString(), uhe );
        } catch( MalformedURLException mue ) {
            throw new SmbException( url.toString(), mue );
        }

        return (String[])list.toArray(new String[list.size()]);
    }
    SmbFile[] listFiles( String wildcard, int searchAttributes,
                SmbFilenameFilter fnf, SmbFileFilter ff ) throws SmbException {
        ArrayList list = new ArrayList();

        if( ff != null && ff instanceof DosFileFilter ) {
            DosFileFilter dff = (DosFileFilter)ff;
            if( dff.wildcard != null ) {
                wildcard = dff.wildcard;
            }
            searchAttributes = dff.attributes;
        }

        try {
            if( url.getHost().length() == 0 || share == null ) {
                doNetEnum( list, true, wildcard, searchAttributes, fnf, ff );
            } else {
                doFindFirstNext( list, true, wildcard, searchAttributes, fnf, ff );
            }
        } catch( UnknownHostException uhe ) {
            throw new SmbException( url.toString(), uhe );
        } catch( MalformedURLException mue ) {
            throw new SmbException( url.toString(), mue );
        }

        return (SmbFile[])list.toArray(new SmbFile[list.size()]);
    }
    void doNetEnum( ArrayList list,
                boolean files,
                String wildcard,
                int searchAttributes,
                SmbFilenameFilter fnf,
                SmbFileFilter ff ) throws SmbException,
                        UnknownHostException, MalformedURLException {
        SmbComTransaction req;
        SmbComTransactionResponse resp;
        int listType = url.getHost().length() == 0 ? 0 : getType();
        String p = url.getPath();

        if( p.lastIndexOf( '/' ) != ( p.length() - 1 )) {
            throw new SmbException( url.toString() + " directory must end with '/'" );
        }

        switch( listType ) {
            case 0:
                connect0();
                req = new NetServerEnum2( tree.session.transport.server.oemDomainName,
                        NetServerEnum2.SV_TYPE_DOMAIN_ENUM );
                resp = new NetServerEnum2Response();
                break;
            case TYPE_WORKGROUP:
                req = new NetServerEnum2( url.getHost(), NetServerEnum2.SV_TYPE_ALL );
                resp = new NetServerEnum2Response();
                break;
            case TYPE_SERVER:
                req = new NetShareEnum();
                resp = new NetShareEnumResponse();
                break;
            default:
                throw new SmbException( "The requested list operations is invalid: " + url.toString() );
        }

            boolean more;
        do {
            int n;

            send( req, resp );

            more = resp.status == SmbException.ERROR_MORE_DATA;

            if( resp.status != SmbException.ERROR_SUCCESS &&
                    resp.status != SmbException.ERROR_MORE_DATA ) {
                throw new SmbException( resp.status, true );
            }

            n = more ? resp.numEntries - 1 : resp.numEntries;
            for( int i = 0; i < n; i++ ) {
                FileEntry e = resp.results[i];
                String name = e.getName();
                if( fnf != null && fnf.accept( this, name ) == false ) {
                    continue;
                }
                if( name.length() > 0 ) {
                    SmbFile f = new SmbFile( this, name,
                                e.getType(),
                                ATTR_READONLY | ATTR_DIRECTORY, 0L, 0L, 0L );
                    if( ff != null && ff.accept( f ) == false ) {
                        continue;
                    }
                    if( files ) {
                        list.add( f );
                    } else {
                        list.add( name );
                    }
                }
            }
            if( listType != 0 && listType != TYPE_WORKGROUP ) {
                break;
            }
            req.subCommand = (byte)SmbComTransaction.NET_SERVER_ENUM3;
            req.reset( 0, ((NetServerEnum2Response)resp).lastName );
            resp.reset();
        } while( more );
    }
    void doFindFirstNext( ArrayList list,
                boolean files,
                String wildcard,
                int searchAttributes,
                SmbFilenameFilter fnf,
                SmbFileFilter ff ) throws SmbException, UnknownHostException, MalformedURLException {
        SmbComTransaction req;
        Trans2FindFirst2Response resp;
        int sid;
        String path = getUncPath0();
        String p = url.getPath();

        if( p.lastIndexOf( '/' ) != ( p.length() - 1 )) {
            throw new SmbException( url.toString() + " directory must end with '/'" );
        }

        req = new Trans2FindFirst2( path, wildcard, searchAttributes );
        resp = new Trans2FindFirst2Response();

        if( log.level > 2 )
            log.println( "doFindFirstNext: " + req.path );

        send( req, resp );

        sid = resp.sid;
        req = new Trans2FindNext2( sid, resp.resumeKey, resp.lastName );

        resp.subCommand = SmbComTransaction.TRANS2_FIND_NEXT2;

        for( ;; ) {
            for( int i = 0; i < resp.numEntries; i++ ) {
                FileEntry e = resp.results[i];
                String name = e.getName();
                if( name.length() < 3 ) {
                    int h = name.hashCode();
                    if( h == HASH_DOT || h == HASH_DOT_DOT ) {
                        continue;
                    }
                }
                if( fnf != null && fnf.accept( this, name ) == false ) {
                    continue;
                }
                if( name.length() > 0 ) {
                    SmbFile f = new SmbFile( this, name, TYPE_FILESYSTEM,
                            e.getAttributes(), e.createTime(), e.lastModified(), e.length() );
                    if( ff != null && ff.accept( f ) == false ) {
                        continue;
                    }
                    if( files ) {
                        list.add( f );
                    } else {
                        list.add( name );
                    }
                }
            }

            if( resp.isEndOfSearch || resp.numEntries == 0 ) {
                break;
            }

            req.reset( resp.resumeKey, resp.lastName );
            resp.reset();
            send( req, resp );
        }

        send( new SmbComFindClose2( sid ), blank_resp() );
    }

    public void renameTo( SmbFile dest ) throws SmbException {
        if( getUncPath0().length() == 1 || dest.getUncPath0().length() == 1 ) {
            throw new SmbException( "Invalid operation for workgroups, servers, or shares" );
        }
        connect0();
        dest.connect0();

        if( tree.inDfs ) {
            exists();
            dest.exists();
        }
        if( tree != dest.tree ) {
            throw new SmbException( "Invalid operation for workgroups, servers, or shares" );
        }

        if( log.level > 2 )
            log.println( "renameTo: " + unc + " -> " + dest.unc );

        attrExpiration = sizeExpiration = 0;
        dest.attrExpiration = 0;

 
        send( new SmbComRename( unc, dest.unc ), blank_resp() );
    }

    class WriterThread extends Thread {
        byte[] b;
        int n, off;
        boolean ready;
        SmbFile dest;
        SmbException e = null;
        boolean useNTSmbs;
        SmbComWriteAndX reqx;
        SmbComWrite req;
        ServerMessageBlock resp;

        WriterThread() throws SmbException {
            super( "JCIFS-WriterThread" );
            useNTSmbs = tree.session.transport.hasCapability( ServerMessageBlock.CAP_NT_SMBS );
            if( useNTSmbs ) {
                reqx = new SmbComWriteAndX();
                resp = new SmbComWriteAndXResponse();
            } else {
                req = new SmbComWrite();
                resp = new SmbComWriteResponse();
            }
            ready = false;
        }

        synchronized void write( byte[] b, int n, SmbFile dest, int off ) {
            this.b = b;
            this.n = n;
            this.dest = dest;
            this.off = off;
            ready = false;
            notify();
        }

        public void run() {
            synchronized( this ) {
                try {
                    for( ;; ) {
                        notify();
                        ready = true;
                        while( ready ) {
                            wait();
                        }
                        if( n == -1 ) {
                            return;
                        }
                        if( useNTSmbs ) {
                            reqx.setParam( dest.fid, off, n, b, 0, n );
                            dest.send( reqx, resp );
                        } else {
                            req.setParam( dest.fid, off, n, b, 0, n );
                            dest.send( req, resp );
                        }
                    }
                } catch( SmbException e ) {
                    this.e = e;
                } catch( Exception x ) {
                    this.e = new SmbException( "WriterThread", x );
                }
                notify();
            }
        }
    }
    void copyTo0( SmbFile dest, byte[][] b, int bsize, WriterThread w,
            SmbComReadAndX req, SmbComReadAndXResponse resp ) throws SmbException {
        int i;

        if( attrExpiration < System.currentTimeMillis() ) {
            attributes = ATTR_READONLY | ATTR_DIRECTORY;
            createTime = 0L;
            lastModified = 0L;
            isExists = false;

            Info info = queryPath( getUncPath0(),
                    Trans2QueryPathInformationResponse.SMB_QUERY_FILE_BASIC_INFO );
            attributes = info.getAttributes();
            createTime = info.getCreateTime();
            lastModified = info.getLastWriteTime();


            isExists = true;
            attrExpiration = System.currentTimeMillis() + attrExpirationPeriod;
        }

        if( isDirectory() ) {
            SmbFile[] files;
            SmbFile ndest;

            String path = dest.getUncPath0();
            if( path.length() > 1 ) {
                try {
                    dest.mkdir();
                    dest.setPathInformation( attributes, createTime, lastModified );
                } catch( SmbException se ) {
                    if( se.getNtStatus() != NtStatus.NT_STATUS_ACCESS_DENIED &&
                            se.getNtStatus() != NtStatus.NT_STATUS_OBJECT_NAME_COLLISION ) {
                        throw se;
                    }
                }
            }

            files = listFiles( "*", ATTR_DIRECTORY | ATTR_HIDDEN | ATTR_SYSTEM, null, null );
            try {
                for( i = 0; i < files.length; i++ ) {
                    ndest = new SmbFile( dest,
                                    files[i].getName(),
                                    files[i].type,
                                    files[i].attributes,
                                    files[i].createTime,
                                    files[i].lastModified,
                                    files[i].size );
                    files[i].copyTo0( ndest, b, bsize, w, req, resp );
                }
            } catch( UnknownHostException uhe ) {
                throw new SmbException( url.toString(), uhe );
            } catch( MalformedURLException mue ) {
                throw new SmbException( url.toString(), mue );
            }
        } else {
            int off;

try {
            open( SmbFile.O_RDONLY, ATTR_NORMAL, 0 );
            try {
                dest.open( SmbFile.O_CREAT | SmbFile.O_WRONLY | SmbFile.O_TRUNC |
                        SmbComNTCreateAndX.FILE_WRITE_ATTRIBUTES << 16, attributes, 0 );
            } catch( SmbAuthException sae ) {
                if(( dest.attributes & ATTR_READONLY ) != 0 ) {
                    dest.setPathInformation( dest.attributes & ~ATTR_READONLY, 0L, 0L );
                    dest.open( SmbFile.O_CREAT | SmbFile.O_WRONLY | SmbFile.O_TRUNC |
                            SmbComNTCreateAndX.FILE_WRITE_ATTRIBUTES << 16, attributes, 0 );
                } else {
                    throw sae;
                }
            }

            i = off = 0;
            for( ;; ) {
                req.setParam( fid, off, bsize );
                resp.setParam( b[i], 0 );
                send( req, resp );

                synchronized( w ) {
                    while( !w.ready ) {
                        try {
                            w.wait();
                        } catch( InterruptedException ie ) {
                            throw new SmbException( dest.url.toString(), ie );
                        }
                    }
                    if( w.e != null ) {
                        throw w.e;
                    }
                    if( resp.dataLength <= 0 ) {
                        break;
                    }
                    w.write( b[i], resp.dataLength, dest, off );
                }

                i = i == 1 ? 0 : 1;
                off += resp.dataLength;
            }

            dest.send( new Trans2SetFileInformation(
                    dest.fid, attributes, createTime, lastModified ),
                    new Trans2SetFileInformationResponse() );
            dest.close( 0L );
            close();
} catch( Exception ex ) {
    if( log.level > 1 )
        ex.printStackTrace( log );
}
        }
    }
    public void copyTo( SmbFile dest ) throws SmbException {
        SmbComReadAndX req;
        SmbComReadAndXResponse resp;
        WriterThread w;
        int bsize;
        byte[][] b;

        if( share == null || dest.share == null) {
            throw new SmbException( "Invalid operation for workgroups or servers" );
        }

        req = new SmbComReadAndX();
        resp = new SmbComReadAndXResponse();

        connect0();
        dest.connect0();

        if( tree.inDfs ) {
            exists();
            dest.exists();
        }

        try {
            if (getAddress().equals( dest.getAddress() ) &&
                        canon.regionMatches( true, 0, dest.canon, 0,
                                Math.min( canon.length(), dest.canon.length() ))) {
                throw new SmbException( "Source and destination paths overlap." );
            }
        } catch (UnknownHostException uhe) {
        }

        w = new WriterThread();
        w.setDaemon( true );
        w.start();

        SmbTransport t1 = tree.session.transport;
        SmbTransport t2 = dest.tree.session.transport;

        if( t1.snd_buf_size < t2.snd_buf_size ) {
            t2.snd_buf_size = t1.snd_buf_size;
        } else {
            t1.snd_buf_size = t2.snd_buf_size;
        }

        bsize = Math.min( t1.rcv_buf_size - 70, t1.snd_buf_size - 70 );
        b = new byte[2][bsize];

        copyTo0( dest, b, bsize, w, req, resp );
        w.write( null, -1, null, 0 );
    }

    public void delete() throws SmbException {
        if( tree == null || tree.inDfs ) {
            exists();
        }
        getUncPath0();
        delete( unc );
    }
    void delete( String fileName ) throws SmbException {
        if( getUncPath0().length() == 1 ) {
            throw new SmbException( "Invalid operation for workgroups, servers, or shares" );
        }

        if( System.currentTimeMillis() > attrExpiration ) {
            attributes = ATTR_READONLY | ATTR_DIRECTORY;
            createTime = 0L;
            lastModified = 0L;
            isExists = false;

            Info info = queryPath( getUncPath0(),
                    Trans2QueryPathInformationResponse.SMB_QUERY_FILE_BASIC_INFO );
            attributes = info.getAttributes();
            createTime = info.getCreateTime();
            lastModified = info.getLastWriteTime();

            attrExpiration = System.currentTimeMillis() + attrExpirationPeriod;
            isExists = true;
        }

        if(( attributes & ATTR_READONLY ) != 0 ) {
            setReadWrite();
        }

        if( log.level > 2 )
            log.println( "delete: " + fileName );

        if(( attributes & ATTR_DIRECTORY ) != 0 ) {


            try {
                SmbFile[] l = listFiles( "*", ATTR_DIRECTORY | ATTR_HIDDEN | ATTR_SYSTEM, null, null );
                for( int i = 0; i < l.length; i++ ) {
                    l[i].delete();
                }
            } catch( SmbException se ) {
                if( se.getNtStatus() != SmbException.NT_STATUS_NO_SUCH_FILE ) {
                    throw se;
                }
            }

            send( new SmbComDeleteDirectory( fileName ), blank_resp() );
        } else {
            send( new SmbComDelete( fileName ), blank_resp() );
        }

        attrExpiration = sizeExpiration = 0;
    }


    public long length() throws SmbException {
        if( sizeExpiration > System.currentTimeMillis() ) {
            return size;
        }

        if( getType() == TYPE_SHARE ) {
            Trans2QueryFSInformationResponse response;
            int level = Trans2QueryFSInformationResponse.SMB_INFO_ALLOCATION;

            response = new Trans2QueryFSInformationResponse( level );
            send( new Trans2QueryFSInformation( level ), response );

            size = response.info.getCapacity();
        } else if( getUncPath0().length() > 1 && type != TYPE_NAMED_PIPE ) {
            Info info = queryPath( getUncPath0(),
                    Trans2QueryPathInformationResponse.SMB_QUERY_FILE_STANDARD_INFO );
            size = info.getSize();
        } else {
            size = 0L;
        }
        sizeExpiration = System.currentTimeMillis() + attrExpirationPeriod;
        return size;
    }

    public long getDiskFreeSpace() throws SmbException {
        if( getType() == TYPE_SHARE || type == TYPE_FILESYSTEM ) {
            int level = Trans2QueryFSInformationResponse.SMB_FS_FULL_SIZE_INFORMATION;
            try {
                return queryFSInformation(level);
            } catch( SmbException ex ) {
                switch (ex.getNtStatus()) {
                    case NtStatus.NT_STATUS_INVALID_INFO_CLASS:
                    case NtStatus.NT_STATUS_UNSUCCESSFUL: // NetApp Filer
                        // SMB_FS_FULL_SIZE_INFORMATION not supported by the server.
                        level = Trans2QueryFSInformationResponse.SMB_INFO_ALLOCATION;
                        return queryFSInformation(level);
                }
                throw ex;
            }
        }
        return 0L;
    }

    private long queryFSInformation( int level ) throws SmbException {
        Trans2QueryFSInformationResponse response;

        response = new Trans2QueryFSInformationResponse( level );
        send( new Trans2QueryFSInformation( level ), response );

        if( type == TYPE_SHARE ) {
            size = response.info.getCapacity();
            sizeExpiration = System.currentTimeMillis() + attrExpirationPeriod;
        }

        return response.info.getFree();
    }

    public void mkdir() throws SmbException {
        String path = getUncPath0();

        if( path.length() == 1 ) {
            throw new SmbException( "Invalid operation for workgroups, servers, or shares" );
        }


        if( log.level > 2 )
            log.println( "mkdir: " + path );

        send( new SmbComCreateDirectory( path ), blank_resp() );

        attrExpiration = sizeExpiration = 0;
    }

    public void mkdirs() throws SmbException {
        SmbFile parent;

        try {
            parent = new SmbFile( getParent(), auth );
        } catch( IOException ioe ) {
            return;
        }
        if( parent.exists() == false ) {
            parent.mkdirs();
        }
        mkdir();
    }

    public void createNewFile() throws SmbException {
        if( getUncPath0().length() == 1 ) {
            throw new SmbException( "Invalid operation for workgroups, servers, or shares" );
        }
        close( open0( O_RDWR | O_CREAT | O_EXCL, ATTR_NORMAL, 0 ), 0L );
    }

    void setPathInformation( int attrs, long ctime, long mtime ) throws SmbException {
        int f, dir;

        exists();
        dir = attributes & ATTR_DIRECTORY;

        f = open0( O_RDONLY | SmbComNTCreateAndX.FILE_WRITE_ATTRIBUTES << 16,
                dir, dir != 0 ? 0x0001 : 0x0040 );
        send( new Trans2SetFileInformation( f, attrs | dir, ctime, mtime ),
                new Trans2SetFileInformationResponse() );
        close( f, 0L );

        attrExpiration = 0;
    }

    public void setCreateTime( long time ) throws SmbException {
        if( getUncPath0().length() == 1 ) {
            throw new SmbException( "Invalid operation for workgroups, servers, or shares" );
        }

        setPathInformation( 0, time, 0L );
    }
    public void setLastModified( long time ) throws SmbException {
        if( getUncPath0().length() == 1 ) {
            throw new SmbException( "Invalid operation for workgroups, servers, or shares" );
        }

        setPathInformation( 0, 0L, time );
    }

    public int getAttributes() throws SmbException {
        if( getUncPath0().length() == 1 ) {
            return 0;
        }
        exists();
        return attributes & ATTR_GET_MASK;
    }

    public void setAttributes( int attrs ) throws SmbException {
        if( getUncPath0().length() == 1 ) {
            throw new SmbException( "Invalid operation for workgroups, servers, or shares" );
        }
        setPathInformation( attrs & ATTR_SET_MASK, 0L, 0L );
    }

    public void setReadOnly() throws SmbException {
        setAttributes( getAttributes() | ATTR_READONLY );
    }

    public void setReadWrite() throws SmbException {
        setAttributes( getAttributes() & ~ATTR_READONLY );
    }

    public URL toURL() throws MalformedURLException {
        return url;
    }


    public int hashCode() {
        int hash;
        try {
            hash = getAddress().hashCode();
        } catch( UnknownHostException uhe ) {
            hash = getServer().toUpperCase().hashCode();
        }
        getUncPath0();
        return hash + canon.toUpperCase().hashCode();
    }


    public boolean equals( Object obj ) {
        return obj instanceof SmbFile && obj.hashCode() == hashCode();
    }


    public String toString() {
        return url.toString();
    }


    public int getContentLength() {
        try {
            return (int)(length() & 0xFFFFFFFFL);
        } catch( SmbException se ) {
        }
        return 0;
    }

    public long getDate() {
        try {
            return lastModified();
        } catch( SmbException se ) {
        }
        return 0L;
    }

    public long getLastModified() {
        try {
            return lastModified();
        } catch( SmbException se ) {
        }
        return 0L;
    }

    public InputStream getInputStream() throws IOException {
        return new SmbFileInputStream( this );
    }

    public OutputStream getOutputStream() throws IOException {
        return new SmbFileOutputStream( this );
    }
}
