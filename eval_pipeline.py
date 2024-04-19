import json
import os
from tqdm import tqdm
from pathlib import Path
from useful_es_tool import query_data, load_data, get_answer
from ground_truth import Gen_GT
from ragas_evaluation import RAGAs_Eval

class Pipeline():
    def __init__(self):
        self.gt = Gen_GT()
        self.eval = RAGAs_Eval()
    
    def run(self, question_list, contexts_list, answer_list=None, ground_truth_list=None, chat_model='gpt-4-turbo', save_data=True, k=10):
        '''
        Eval_Pipeline最终调用端口, 输入为:
        question_list = [q_1, q_2,...,q_n]  全部问题列表 list(str)
        contexts_list = [c_1, c_2, ..., c_n]   其中c_i = [d_1, d_2, ..., d_m], m=一个问题对应的contexts数量, n=全部数据集问题的数量 list(list(str))
        answer_list = [a_1, a_2, ..., a_n]  每个问题对应的答案 (可选, 默认为None), 如果没有输入, 系统默认仅生成标准答案 list(str)
        ground_truth_list = [g_1, g_2, ..., g_n]   每个问题对应的标准答案 (可选, 默认为None), 如果没有输入, 由系统根据contexts和question生成  list(str)
        chat_model: 生成标准答案的GPT模型 (可选, 默认为'gpt-4-turbo')
        save_data: 是否将数据保存成结构化的数据/是否将数据储存成.json (可选, 默认为True), 会将数据保存在./full或者./gt中
        k: Top-k个contexts用于RAGAs评分 (可选, 默认为10)
        '''
        
        if answer_list is not None:
            if ground_truth_list is None:
                print("生成标准答案中.....")
                ground_truths = []
            for index, question in enumerate(question_list):
                contexts = contexts_list[index]
                answer = answer_list[index]
                if ground_truth_list is None:
                    print(f'Question {index+1}/{len(question_list)}')
                    ground_truth = self.gt.generate_gt(question, contexts, chat_model=chat_model)
                    ground_truths.append(ground_truth)
                else:
                    ground_truth = ground_truth_list[index]

                # 保存data(可选)
                if save_data:
                    data = {"question": question, "contexts":contexts, "ground_truth":ground_truth, "answer": answer}
                    if not os.path.exists('./full'):
                        os.makedirs('./full')
                    with open(f'./full/FULL_{question}.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
            print("\nRAGAs评分中.....")
            if ground_truth_list is None:
                score = self.eval.run(question_list, contexts_list, answer_list, ground_truths, k=k)
            else:
                score = self.eval.run(question_list, contexts_list, answer_list, ground_truth_list, k=k)
            print("\n分数结果已保存至./result/result.xlsx中")
            return score
        else:
            print("仅生成问题的标准答案, 如需进行RAGAs评分, 请提供答案列表answer_list")
            print("生成标准答案中.....")
            ground_truths = []                                       
            for index, question in enumerate(question_list):
                contexts = contexts_list[index]
                ground_truth = self.gt.generate_gt(question, contexts, chat_model=chat_model)
                ground_truths.append(ground_truth)
                
                # 保存data(可选)
                if save_data:
                    data = {"question": question, "contexts":contexts, "ground_truth":ground_truth}
                    # 将生成的ground_truth连同question和contexts一起存入一个json中
                    if not os.path.exists('./gt'):
                        os.makedirs('./gt')
                    with open(f'./gt/GT_{question}.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
            if save_data:
                print("\n标准答案已保存至./gt中") 
            return ground_truths

if __name__ == "__main__":  
    company_name_list = ['东方航空公司', '优刻得科技股份有限公司', '优刻得科技股份有限公司']
    question_body_list = ['主营业务', '主营业务', '该企业的未来发展规划是什么']
    question_list = []
    contexts_list = []
    answer_list = []
    ground_truth_list = []

    folder_path = './full'  # 完整数据储存在result文件夹中
    for file in tqdm(os.listdir(folder_path)):
        # 加载数据
        with open(os.path.join(folder_path, file), 'r', encoding='utf-8') as f:
            data = json.load(f)
            question_list.append(data["question"])
            contexts_list.append(data["contexts"])
            answer_list.append(data["answer"])
            ground_truth_list.append(data["ground_truth"])

    p = Pipeline()

    score = p.run(question_list, contexts_list, answer_list, ground_truth_list, save_data=False, k=10)
    print(score)

# 三种调用方式：
# 1. 用户上传question, contexts, answer, 让系统生成标准答案和评分
    # score = p.run(question_list, contexts_list, answer_list, ground_truth_list=None, save_data=True, k=10)
    # 返回分数列表
# 2. 用户上传question, contexts, answer, ground_truth, 仅让系统生成评分
    # score = p.run(question_list, contexts_list, answer_list, ground_truth_list, save_data=True, k=10)
    # 返回分数列表
# 3. 用户上传question, contexts, 并设置eval=False, 仅让系统生成标准答案
    # ground_truth = p.run(question_list, contexts_list, answer_list, ground_truth_list, save_data=True, k=10)
    # 返回标准答案列表