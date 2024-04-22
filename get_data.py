import os
import json
import requests
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm

# 将./data文件夹中的内容全部转换成lists, 用于后续排序和评价
def get_data_list():
    question_list = []
    contexts_list = []
    answer_list = []

    data_directory = './data'

    for file_name in os.listdir(data_directory):
        file_path = os.path.join(data_directory, file_name)
        if os.path.isfile(file_path) and file_name.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                question_list.append(data['question'])
                contexts_list.append(data['contexts'])
                answer_list.append(data['answer'])
    
    return question_list, contexts_list, answer_list

class Get_Data():
    # 从ElasticSearch中获取contexts
    def get_contexts(self, company_name, question_body, query_size=200):
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
            basic_auth=(ES_USER_NAME, ES_PASSWORD)  # 替换username和密码-----------------------------------------
        )

        # 调用函数执行查询
        index = "company-news"
        response = es.search(
                index=index,
                _source_excludes=["content_embedding", "keywords_embedding"],
                size=query_size,
                query={
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
            )


        data = dict(response)

        # 将context的内容提取出来并存在context_list中
        context_list = []
        for item in data["hits"]["hits"]:
            content = item["_source"]["metadata"]["content"]
            context_list.append(content)
        return context_list


    # 从自研系统中获取答案，作为answer
    def get_answer(self, company_name, question_body):
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
    
    def run(self, company_name, question_body, query_size=200):
        contexts = self.get_contexts(company_name, question_body, query_size=query_size)
        answer = self.get_answer(company_name, question_body)
        question = company_name+question_body
        data = {"question": question, "contexts":contexts, "answer": answer}
        # 将搜集到的资料存储到json file中 
        if not os.path.exists('./data'):
            os.makedirs('./data')
        with open("./data/"+question+".json", "w",encoding='utf-8') as save_file:
            json.dump(dict(data), save_file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    company_name_list = ['东方航空公司', '优刻得科技股份有限公司', '优刻得科技股份有限公司']
    question_body_list = ['主营业务', '主营业务', '该企业的未来发展规划是什么']
    get = Get_Data()

    for index, name in enumerate(tqdm(company_name_list)):
        question_body = question_body_list[index]
        get.run(name, question_body, query_size=30)

    question_list, contexts_list, answer_list = get_data_list()

    print("Questions:", question_list)
    print("Contexts:", contexts_list)
    print("Answers:", answer_list)