import utils_new as utils
import numpy as np
import scipy.sparse as sps
from External_Libraries.Notebooks_utils.data_splitter import train_test_holdout
from External_Libraries.Similarity.Compute_Similarity_Python import Compute_Similarity_Python
from External_Libraries.Evaluation.Evaluator import EvaluatorHoldout
from External_Libraries.KNN.ItemKNNCFRecommender import ItemKNNCFRecommender
from External_Libraries.KNN.UserKNNCFRecommender import UserKNNCFRecommender
from External_Libraries.KNN.ItemKNNCBFRecommender import ItemKNNCBFRecommender
from External_Libraries.ParameterTuning.SearchBayesianSkopt import SearchBayesianSkopt
from External_Libraries.ParameterTuning.SearchAbstractClass import SearchInputRecommenderArgs
from skopt.space import Integer, Categorical
import os
from External_Libraries.DataIO import DataIO
from External_Libraries.Base.Recommender_utils import check_matrix
from External_Libraries.Base.BaseSimilarityMatrixRecommender import BaseItemSimilarityMatrixRecommender
from External_Libraries.MatrixFactorization.PureSVDRecommender import PureSVDRecommender
import evaluator

URM_all = sps.csr_matrix(sps.load_npz("../../Dataset/old/data_all.npz"))
URM_train = sps.csr_matrix(sps.load_npz("../../Dataset/old/data_train.npz"))
URM_test = sps.csr_matrix(sps.load_npz("../../Dataset/old/data_test.npz"))

features1 = utils.get_second_column("../../Dataset/ICM/ICM_sub_class.csv")
features2 = utils.get_second_column("../../Dataset/ICM/ICM_price.csv")
features3 = utils.get_second_column("../../Dataset/ICM/ICM_asset.csv")
features = features1 + features2 + features3

items1 = utils.get_first_column("../../Dataset/ICM/ICM_sub_class.csv")
items2 = utils.get_first_column("../../Dataset/ICM/ICM_price.csv")
items3 = utils.get_first_column("../../Dataset/ICM/ICM_asset.csv")
items = items1 + items2 + items3

ones = np.ones(len(features))

n_items = URM_all.shape[1]
n_tags = max(features) + 1

ICM_shape = (n_items, n_tags)
ICM_all = sps.coo_matrix((ones, (items, features)), shape=ICM_shape)
ICM_all = ICM_all.tocsr()


def sort_list(list1, list2):
    z = [x for _,x in sorted(zip(list2, list1), reverse=True)]
    return z

def tuning():
    URM_train, URM_test = train_test_holdout(URM_all, train_perc=0.8)
    URM_train, URM_validation = train_test_holdout(URM_train, train_perc=0.9)

    evaluator_validation = EvaluatorHoldout(URM_validation, cutoff_list=[5])
    evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[5, 10])

    recommender_class = ItemKNNCBFRecommender

    parameterSearch = SearchBayesianSkopt(recommender_class,
                                          evaluator_validation=evaluator_validation,
                                          evaluator_test=evaluator_test)

    hyperparameters_range_dictionary = {}
    hyperparameters_range_dictionary["topK"] = Integer(5, 70)
    hyperparameters_range_dictionary["shrink"] = Integer(20, 120)
    hyperparameters_range_dictionary["similarity"] = Categorical(["jaccard"])
    hyperparameters_range_dictionary["normalize"] = Categorical([False])

    recommender_input_args = SearchInputRecommenderArgs(
        CONSTRUCTOR_POSITIONAL_ARGS=[URM_train, ICM_all],
        CONSTRUCTOR_KEYWORD_ARGS={},
        FIT_POSITIONAL_ARGS=[],
        FIT_KEYWORD_ARGS={}
    )

    output_folder_path = "result_experiments/"

    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    n_cases = 10
    metric_to_optimize = "MAP"

    parameterSearch.search(recommender_input_args,
                           parameter_search_space=hyperparameters_range_dictionary,
                           n_cases=n_cases,
                           n_random_starts=1,
                           save_model="no",
                           output_folder_path=output_folder_path,
                           output_file_name_root=recommender_class.RECOMMENDER_NAME,
                           metric_to_optimize=metric_to_optimize
                           )

    data_loader = DataIO(folder_path=output_folder_path)
    search_metadata = data_loader.load_data(recommender_class.RECOMMENDER_NAME + "_metadata.zip")

    print(search_metadata)

    best_parameters = search_metadata["hyperparameters_best"]
    print(best_parameters)

class ItemKNNScoresHybridRecommender(BaseItemSimilarityMatrixRecommender):

    RECOMMENDER_NAME = "ItemKNNScoresHybridRecommender"

    def __init__(self, URM_train, Recommender_1, Recommender_2, Recommender_3, Recommender_4):
        super(ItemKNNScoresHybridRecommender, self).__init__(URM_train)

        self.URM_train = check_matrix(URM_train.copy(), 'csr')
        self.Recommender_1 = Recommender_1
        self.Recommender_2 = Recommender_2
        self.Recommender_3 = Recommender_3
        self.Recommender_4 = Recommender_4

    def fit(self, alpha, beta, gamma, delta):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta

    def _compute_item_score(self, user_id_array, items_to_compute):
        item_weights_1 = self.Recommender_1._compute_item_score(user_id_array)
        item_weights_2 = self.Recommender_2._compute_item_score(user_id_array)
        item_weights_3 = self.Recommender_3._compute_item_score(user_id_array)
        item_weights_4 = self.Recommender_4._compute_item_score(user_id_array)

        item_weights = item_weights_1 * self.alpha + item_weights_2 * self.beta + item_weights_3 * self.gamma + item_weights_4 * self.delta

        return item_weights

class TopPopHybridReccomender(BaseItemSimilarityMatrixRecommender):
    RECOMMENDER_NAME = "ItemKNNScoresHybridRecommender"

    def __init__(self, URM_train, Recommender_1, Recommender_2, Recommender_3):
        super(TopPopHybridReccomender, self).__init__(URM_train)

        self.URM_train = check_matrix(URM_train.copy(), 'csr')
        self.Recommender_1 = Recommender_1
        self.Recommender_2 = Recommender_2
        self.Recommender_3 = Recommender_3

    def fit(self, alpha, beta, gamma):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def _compute_item_score(self, user_id_array, items_to_compute):
        item_weights_1 = self.Recommender_1._compute_item_score(user_id_array)
        item_weights_2 = self.Recommender_2._compute_item_score(user_id_array)
        item_weights_3 = self.Recommender_3._compute_item_score(user_id_array)

        item_weights = item_weights_1 * self.alpha + item_weights_2 * self.beta + item_weights_3 * self.gamma

        return item_weights

class ItemCFKNNRecommender(object):

    def __init__(self, URM):
        self.URM = URM

    def fit(self, topK, shrink, normalize=True, similarity="jaccard"):
        similarity_object = Compute_Similarity_Python(self.URM, shrink=shrink,
                                                      topK=topK, normalize=normalize,
                                                      similarity=similarity)

        self.W_sparse = similarity_object.compute_similarity()

    def recommend(self, user_id, at=None, exclude_seen=True):
        # compute the scores using the dot product
        user_profile = self.URM[user_id]
        scores = user_profile.dot(self.W_sparse).toarray().ravel()

        if exclude_seen:
            scores = self.filter_seen(user_id, scores)

        # rank items
        ranking = scores.argsort()[::-1]

        return ranking[:at]

    def filter_seen(self, user_id, scores):
        start_pos = self.URM.indptr[user_id]
        end_pos = self.URM.indptr[user_id + 1]

        user_profile = self.URM.indices[start_pos:end_pos]

        scores[user_profile] = -np.inf

        return scores

class UserCFKNNRecommender(object):

    def __init__(self, URM, URM_train):
        self.URM = URM
        self.test = URM_train

    def fit(self, topK=50, shrink=100, normalize=True, similarity="jaccard"):
        similarity_object = Compute_Similarity_Python(self.URM.T, shrink=shrink,
                                                      topK=topK, normalize=normalize,
                                                      similarity=similarity)

        self.W_sparse = similarity_object.compute_similarity()

    def recommend(self, user_id, at=None, exclude_seen=True):
        # compute the scores using the dot product

        scores = self.W_sparse[user_id, :].dot(self.URM).toarray().ravel()

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

URM_train, URM_test = train_test_holdout(URM_all, train_perc=0.8)
URM_train, URM_validation = train_test_holdout(URM_train, train_perc = 0.9)

itemColl = ItemKNNCFRecommender(URM_train)
#itemColl.fit(shrink=106, topK=63, similarity="jaccard")

userColl = UserKNNCFRecommender(URM_train)
userColl.fit(shrink=100, topK=3, similarity="cosine")

itemCont = ItemKNNCBFRecommender(URM_all, ICM_all)
#itemCont.fit(shrink=120, topK=5, similarity="jaccard")

pureSVD = PureSVDRecommender(URM_all)
#pureSVD.fit()

hybridrecommender = ItemKNNScoresHybridRecommender(URM_train, userColl, userColl, userColl, userColl)



users = utils.get_target_users("../../Dataset/target_users.csv")
evaluator_validation = EvaluatorHoldout(URM_validation, cutoff_list=[5])
evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[5, 10])
'''
with open("../../../Outputs/tuning_results.csv", 'w') as fr:
'''
'''
for alpha in [0.7, 0.75, 0.8]:
    for beta in [0.2, 0.25, 0.3, 0.35]:
        print("ALPHA:{0}, BETA: {1}, GAMMA:{2}, DELTA:{3}".format(alpha, beta, 0.15, 0.05))
        hybridrecommender.fit(alpha, 0.25, 0.15, 0.05)
        #evaluator.evaluate(users, hybridrecommender, URM_test)
        print(evaluator_test.evaluateRecommender(hybridrecommender))

     
        with open("../../../Outputs/temp.csv", 'w') as f:
            f.write("user_id,item_list\n")
            for user_id in users:
                recommendations, scores = hybridrecommender.recommend(user_id, return_scores=True)
                f.write(str(user_id) + ", " + utils.trim(recommendations[:10]) + "\n")
        similarity = utils.compare_csv("../../../Outputs/truth2.csv", "../../../Outputs/temp.csv")
        fr.write("ALPHA:{0}, BETA: {1}, GAMMA:{2}, DELTA:{3}\n".format(alpha, beta, gamma, delta))
        fr.write(similarity + "\n\n")
        '''



'''
users = utils.get_target_users("../../../Dataset/target_users.csv")
hybridrecommender.fit(1, 0.5, 0.25, 0.25)
evaluator.evaluate(users, hybridrecommender, URM_test)

'''

hybridrecommender.fit(1, 0, 0, 0)
evaluator.evaluate(users, hybridrecommender, URM_test)
'''
with open("../../../Outputs/HappyNewHybrid_0.8_0.25_0.15_0.05.csv", 'w') as f:
    f.write("user_id,item_list\n")
    for user_id in users:
        recommendations, scores = hybridrecommender.recommend(user_id, return_scores = True)
        f.write(str(user_id) + ", " + utils.trim(recommendations[:10]) + "\n")
'''
'''
users = utils.get_target_users("../../../Dataset/target_users_cold.csv")

topPop = topPop()
topPop.fit(URM_train)

topPopCluster = topPopCluster()
topPopCluster.fit()

lightFMTopPop = lightFMTopPop()
lightFMTopPop.fit()

hybridTopPop = TopPopHybridReccomender(URM_train, topPop, topPopCluster, lightFMTopPop)

hybridTopPop.fit(1, 0, 0)
evaluator.evaluate(users, hybridTopPop, URM_all)
print("\n\n")

hybridTopPop.fit(0, 1, 0)
evaluator.evaluate(users, hybridTopPop, URM_all)
print("\n\n")

hybridTopPop.fit(0, 0, 1)
evaluator.evaluate(users, hybridTopPop, URM_all)
print("\n\n")
'''





