import os
import json
import requests
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# 从ElasticSearch中获取contexts
def query_data(company_name, question_body, query_size=200):
    if not os.path.exists('./data'):
            os.makedirs('./data')
    if f"{company_name}{question_body}.json" not in os.listdir('./data'):
        '''
        company_name: 需要搜索公司的名称，字符串               "优刻得科技股份有限公司"
        question_body: 需要搜索的问题的主题内容，字符串         "主营业务"
        query_size: 需要搜集资料的长度, 默认值为200
        '''
        # 连接到Elasticsearch
        load_dotenv()
        ES_SERVER_ADDRESS = os.getenv("ES_SERVER_ADDRESS")
        ES_USER_NAME = os.getenv("ES_USER_NAME")
        ES_PASSWORD = os.getenv("ES_PASSWORD")

        es = Elasticsearch(
            [ES_SERVER_ADDRESS],  # Elasticsearch地址
            http_auth=(ES_USER_NAME, ES_PASSWORD)  # 替换username和密码-----------------------------------------
        )

        # 调用函数执行查询
        index = "company-news"
        query_body = {
            "_source": {
                "excludes": ["content_embedding", "keywords_embedding"]
            },
            "size": query_size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "match_phrase": {
                                "collection_info.collect_id": company_name
                            }
                        }
                    ],
                    "should": [
                        {
                            "match": {
                                "metadata.content": {
                                    "query": question_body,
                                    "boost": 8
                                }
                            }
                        }
                    ]
                }
            }
        }

        # 执行查询
        response = es.search(index=index, body=query_body)  # 替换为你的索引名称

        
        # 将搜集到的资料存储到json file中 
        with open("./data/"+company_name+question_body+".json", "w",encoding='utf-8') as save_file:
            json.dump(dict(response), save_file, ensure_ascii=False, indent=2)


def load_data(filename):
    # 加载数据（问题作为文件名）
    with open("./data/"+filename+'.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # 将context的内容提取出来并存在context_list中
    context_list = []
    for item in data["hits"]["hits"]:
        content = item["_source"]["metadata"]["content"]
        context_list.append(content)
    return context_list

# 从自研系统中获取答案，作为answer
def get_answer(company_name, question_body):
    response = ''
    url = "http://117.50.190.205:8001/qa"
    params = {
        "message": question_body,
        "company_name": company_name
    }
    s = requests.Session()

    while response == '':
        with s.get(url, params=params, stream=True) as resp:
            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if line:
                        response = line.decode('utf-8')
                        #print(line.decode('utf-8'))
            else:
                print(f'错误：服务器返回状态码 {resp.status_code}, 请检查是否关闭了VPN')
    
        if response=='':
            print('错误：无法获得响应信息，正在重新获取......')

    response = response.split('data: ', 1)[1]
    response = json.loads(response)
    return response['content']