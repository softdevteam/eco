import json

def show_stats(filename):
    with open(filename) as f:
        print(filename)
        l = json.load(f)
        total   = sum([sum(x) for x in l])
        valid   = sum([x[0] for x in l])
        invalid = sum([x[1] for x in l])
        novalid = sum([x[2] for x in l])
        noerror = sum([x[3] for x in l])
        nomulti = sum([x[4] for x in l])
        print("  Valid insertion:      {}/{} = {:.3}%".format(  valid, total, float(valid)/total*100 if total > 0 else 0.0))
        print("  Invalid insertion:    {}/{} = {:.3}%".format(invalid, total, float(invalid)/total*100 if total > 0 else 0.0))
        print("  No insertion (Valid): {}/{} = {:.3}%".format(novalid, total, float(novalid)/total*100 if total > 0 else 0.0))
        print("  No insertion (Error): {}/{} = {:.3}%".format(noerror, total, float(noerror)/total*100 if total > 0 else 0.0))
        print("  No insertion (Multi): {}/{} = {:.3}%".format(nomulti, total, float(nomulti)/total*100 if total > 0 else 0.0))

show_stats("javaphp_log.json")
show_stats("javasql_log.json")
show_stats("javalua_log.json")

show_stats("luaphp_log.json")
show_stats("luasql_log.json")
show_stats("luajava_log.json")

show_stats("phpjava_log.json")
show_stats("phpsql_log.json")
show_stats("phplua_log.json")

show_stats("sqlphp_log.json")
show_stats("sqljava_log.json")
show_stats("sqllua_log.json")
