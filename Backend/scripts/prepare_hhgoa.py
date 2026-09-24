"""Normalize IEEE-CIS-style HHGOA CSVs for graph/schema.gsql.

The HHGOA README is authoritative for source filenames. This script uses common
IEEE-CIS column names and also accepts normalized source files when present.
"""
import argparse, csv, json, os, re
from pathlib import Path

def files(root):
    return {p.name.lower(): p for p in Path(root).glob("*.csv")}

def pick(mapping, *names, default=""):
    for n in names:
        if n in mapping and mapping[n] not in (None, ""):
            return mapping[n]
    return default

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            yield {norm(k): v for k, v in row.items()}

def write(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        out = csv.DictWriter(f, fieldnames=fields)
        out.writeheader(); out.writerows(rows)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--input-dir", required=True); ap.add_argument("--output-dir", required=True)
    a = ap.parse_args(); src = files(a.input_dir); out = Path(a.output_dir)
    tx = next((p for n,p in src.items() if "transaction" in n or n == "train_transaction.csv"), None)
    if not tx: raise SystemExit("No transaction CSV found; read the HHGOA dataset README and provide its transaction file.")
    tx_fields = ["transaction_id","account_id","event_time","amount","currency","is_online","model_risk_score","merchant_id","merchant_category","country","device_id","raw_features"]
    transactions=[]; accounts={}; devices={}
    for r in read_csv(tx):
        tid=pick(r,"transactionid","transaction_id"); aid=pick(r,"account_id","customer_id","card_id",default="account_"+tid)
        did=pick(r,"device_id","deviceinfo","device_id_hash")
        known={k:pick(r,k) for k in ("transactionid","account_id","transaction_id","event_time","transactiondt","amount","currency","is_online","is fraud","isfraud","merchant_id","merchantid","merchant_category","mcc","country","device_id","deviceinfo")}
        transactions.append({"transaction_id":tid,"account_id":aid,"event_time":pick(r,"event_time","transactiondt"),"amount":pick(r,"amount"),"currency":pick(r,"currency","card_country"),"is_online":str(bool(pick(r,"is_online","card_present"))).lower(),"model_risk_score":pick(r,"model_risk_score","risk_score","dist1"),"merchant_id":pick(r,"merchant_id","merchantid"),"merchant_category":pick(r,"merchant_category","mcc"),"country":pick(r,"country","addr_country"),"device_id":did,"raw_features":json.dumps(known,separators=(",",":"))})
        accounts.setdefault(aid,{"account_id":aid,"customer_id":pick(r,"customer_id","card_id",default=aid),"first_seen":pick(r,"event_time","transactiondt"),"last_seen":pick(r,"event_time","transactiondt"),"status":"active","country":pick(r,"country","addr_country"),"risk_score":pick(r,"risk_score","model_risk_score","dist1"),"attributes":"{}","device_id":did,"transaction_count":1})
        if did: devices.setdefault(did,{"device_id":did,"first_seen":pick(r,"event_time","transactiondt"),"last_seen":pick(r,"event_time","transactiondt"),"device_type":"unknown","attributes":"{}"})
    write(out/"transactions.csv",tx_fields,transactions)
    write(out/"accounts.csv",["account_id","customer_id","first_seen","last_seen","status","country","risk_score","attributes","device_id","transaction_count"],accounts.values())
    write(out/"customers.csv",["customer_id","first_seen","last_seen","attributes"],[{"customer_id":v["customer_id"],"first_seen":v["first_seen"],"last_seen":v["last_seen"],"attributes":"{}"} for v in accounts.values()])
    write(out/"devices.csv",["device_id","first_seen","last_seen","device_type","attributes"],devices.values())
    for name, fields in (("identities.csv",["identity_id","identity_type","normalized_value","attributes"]),("prior_cases.csv",["case_id","opened_at","closed_at","outcome","fraud_type","risk_level","summary","attributes"])):
        if name.lower() not in src: write(out/name,fields,[])
    print(f"wrote {len(transactions)} transactions, {len(accounts)} accounts, {len(devices)} devices to {out}")

if __name__ == "__main__": main()
