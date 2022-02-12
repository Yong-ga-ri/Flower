from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import pymongo
import boto3
import os
import json
from elasticsearch import Elasticsearch, helpers
from flask_cors import CORS, cross_origin
from bson.json_util import dumps, loads


app = Flask(__name__)
CORS(app)

es = Elasticsearch(
    hosts=['http://elasticsearch:9200'],
    http_auth=('elastic', 'changeme')
)

mongo_info = os.environ['mondb_URI']

app.config['FLASKS3_BUCKET_NAME'] = 'team-flower'
app.config['UPLOAD_FOLDER'] = "/backend/Images"
app.config['directory'] = "root_directory"
bucket_name = app.config['FLASKS3_BUCKET_NAME']
rootFolder = app.config['directory']

s3 = boto3.client(
    service_name="s3",
    region_name=os.environ['s3_region_name'],
    aws_access_key_id=os.getenv('s3_aws_access_key_id'),
    aws_secret_access_key=os.getenv('s3_aws_secret_access_key'),
    endpoint_url=os.getenv('endpoint_url')
)

myclient = pymongo.MongoClient(
    mongo_info
)
mydb = myclient.flowerdb
myinform = mydb.inform
myurl = mydb.photo_url

doc = myinform.find()

# corsur to json
json_data = dumps(list(doc))


@app.route('/a')
def asdf():

    return 'Hello, Pybo!'


@app.route('/api/v1/initialize')
def hello_pybo():

    with open('mapping.json', 'r') as f:
        mapping = json.load(f)

    index = "flower_idx"

    es.indices.create(index=index, body=mapping)

    with open("local_dict.json", encoding='utf-8') as json_file:
        json_data = json.loads(json_file.read())

    helpers.bulk(es, json_data, index=index)

    return 'Hello, Pybo!'


@app.route('/api/v1/search', methods=["GET"])
def searchAPI():
    order = request.args.get('q')
    docs = es.search(
        index='flower_idx',
        body={
            "query": {
                "multi_match": {
                    "query": order,
                    "fields": ["name", "flowerMeaning", "water", "sunlight", "caution"]
                }
            }
        }
    )

    data_list = docs['hits']

    return data_list


@app.route('/api/v1/upload', methods=["POST"])
def uploadFile():

    file = request.files['upload_files']
    # 한글 이름의 파일 입력시 validation이 안되는 문제가 존재
    file.filename = secure_filename(file.filename)

    # backend 서버에 파일 저장
    file.save(os.path.join(
        app.config['UPLOAD_FOLDER'], file.filename))

    # s3 bucket에 이미지 파일 저장
    file_path = app.config['UPLOAD_FOLDER'] + "/" + file.filename
    s3.upload_file(
        file_path, rootFolder, file.filename)

    file_dir = os.getenv('endpoint_url') + "/" + \
        app.config['directory'] + "/" + file.filename

    file_db = {
        "URL": file_dir
    }

    myurl.insert_one(file_db)

    return_json = json.dumps(file_path)

    return return_json


if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000)

# 1 이미지 받아서 데이터베이스에 저장

# 1-1 국화 -> 정보를 데이터베이스에서 조회 유저 반환
