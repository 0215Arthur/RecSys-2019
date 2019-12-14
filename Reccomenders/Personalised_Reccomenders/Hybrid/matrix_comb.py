import numpy as np
import scipy.sparse as sps
import utils_new as util
import External_Libraries.Recommender_utils as mauri
import External_Libraries.Notebooks_utils.evaluation_function as eval


def normalize(URM, min, max):
    print(min,max)
    for i in range(URM.nnz):
        URM.data[i] = (URM.data[i]-min)/(max-min)
    return URM


class Reccomender(object):

    def __init__(self, URM, URM_t):
        self.URM = URM
        self.test = URM_t

    def fit(self, similarity_matrix):
        self.W_sparse = similarity_matrix

    def recommend(self, user_id, at=10, exclude_seen=True):
        # compute the scores using the dot product
        user_profile = self.URM[user_id]
        scores = user_profile.dot(self.W_sparse).toarray().ravel()

        if exclude_seen:
            scores = self.filter_seen(user_id, scores)

        # rank items
        ranking = scores.argsort()[::-1]

        return ranking[:at]

    def filter_seen(self, user_id, scores):
        start_pos = self.test.indptr[user_id]
        end_pos = self.test.indptr[user_id + 1]

        user_profile = self.test.indices[start_pos:end_pos]

        scores[user_profile] = -np.inf

        return scores

cumulative_precision = 0.0
cumulative_recall = 0.0
cumulative_MAP = 0.0
num_eval = 0
URM_1 = sps.csr_matrix(sps.load_npz("../../../Dataset/CB-Sim.npz"))
URM_2 = sps.csr_matrix(sps.load_npz("../../../Dataset/Col-Sim.npz"))
URM_3 = sps.csr_matrix(sps.load_npz("../../../Dataset/Slim-Sim.npz"))
URM_all = sps.csr_matrix(sps.load_npz("../../../Dataset/data_all.npz"))
URM_test = sps.csr_matrix(sps.load_npz("../../../Dataset/data_test.npz"))
print(URM_1.shape)
print(URM_2.shape)
print(max(URM_1.data))
print(max(URM_2.data))
print(min(URM_1.data))
print(min(URM_2.data))
reccomender = Reccomender(URM_all,URM_test)
targetUsers = util.get_target_users("../../../dataset/target_users_other.csv")
for i in range(0,10):
    for j in range (0,10):
        for z in range(0,10):
            for norm in (True, False):
                num_eval = 0
                a = 1 - i*0.1
                b = 1 - j*0.1
                c = 1 - z*0.1
                if norm:
                    URM_3 = normalize(URM_3,min(min(URM_1.data), min(URM_2.data)),max(max(URM_1.data), max(URM_2.data)))
                similarity_matrix = mauri.similarityMatrixTopK(a*URM_1 + b*URM_2 + c*URM_3)
                reccomender.fit(similarity_matrix)
                for user in targetUsers:
                    if num_eval % 1000 == 0:
                        print("Evaluated user {} of {}".format(num_eval, len(targetUsers)))

                    start_pos = URM_test.indptr[user]
                    end_pos = URM_test.indptr[user + 1]
                    relevant_items = np.array([0])
                    if end_pos - start_pos > 0:

                        relevant_items = URM_test.indices[start_pos:end_pos]
                        # print(relevant_items)

                        is_relevant = np.in1d(reccomender.recommend(user), relevant_items, assume_unique=True)
                    else:
                        # num_eval += 1
                        is_relevant = np.array([False, False, False, False, False, False, False, False, False, False])

                    num_eval += 1
                    cumulative_precision += eval.precision(is_relevant, relevant_items)
                    cumulative_recall += eval.recall(is_relevant, relevant_items)
                    cumulative_MAP += eval.MAP(is_relevant, relevant_items)

                '''''
                with open("../../../Outputs/testSslim.csv", 'w') as f:
                    f.write("user_id,item_list\n")
                    for user_id in targetUsers:
                        f.write(str(user_id) + "," + util.trim(np.array(reccomender.recommend(user_id))) + "\n")
                
                
                
                with open("../../../Outputs/Sslim.csv", 'w') as f:
                    f.write("user_id,item_list\n")
                    for user_id in targetUsers:
                        f.write(str(user_id) + "," + util.trim(np.array(reccomender.recommend(user_id))) + "\n")
                util.compare_csv("../../../Outputs/truth.csv", "../../../Outputs/Sslim.csv")
                '''

                cumulative_precision /= num_eval
                cumulative_recall /= num_eval
                cumulative_MAP /= num_eval

                '''  
                print("Recommender performance is: Precision = {:.4f}, Recall = {:.4f}, MAP@10 = {:.4f}".format(
                    cumulative_precision, cumulative_recall, cumulative_MAP))
                
                with open("../../../Outputs/UserSlim.csv", 'w') as f:
                    f.write("user_id\n")
                    for user_id in goodUsers:
                        f.write(str(user_id) + "\n")
                    '''
                result_dict = {
                    "precision": cumulative_precision,
                    "recall": cumulative_recall,
                    "MAP": cumulative_MAP,
                    "ALPHA": a,
                    "BETA": b,
                    "GAMMA": c,
                    "NORM": norm
                }
                print(result_dict)

                #util.compare_csv("../../../Outputs/truth.csv", "../../../Outputs/testSslim.csv")


