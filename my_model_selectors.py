import math
import statistics
import warnings

import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import KFold
from asl_utils import combine_sequences


class ModelSelector(object):
    '''
    base class for model selection (strategy design pattern)
    '''

    def __init__(self, all_word_sequences: dict, all_word_Xlengths: dict, this_word: str,
                 n_constant=3,
                 min_n_components=2, max_n_components=10,
                 random_state=14, verbose=False):
        self.words = all_word_sequences
        self.hwords = all_word_Xlengths
        self.sequences = all_word_sequences[this_word]
        self.X, self.lengths = all_word_Xlengths[this_word]
        self.this_word = this_word
        self.n_constant = n_constant
        self.min_n_components = min_n_components
        self.max_n_components = max_n_components
        self.random_state = random_state
        self.verbose = verbose

    def select(self):
        raise NotImplementedError

    def base_model(self, num_states):
        # with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        # warnings.filterwarnings("ignore", category=RuntimeWarning)
        try:
            hmm_model = GaussianHMM(n_components=num_states, covariance_type="diag", n_iter=1000,
                                    random_state=self.random_state, verbose=False).fit(self.X, self.lengths)
            if self.verbose:
                print("model created for {} with {} states".format(self.this_word, num_states))
            return hmm_model
        except:
            if self.verbose:
                print("failure on {} with {} states".format(self.this_word, num_states))
            return None


class SelectorConstant(ModelSelector):
    """ select the model with value self.n_constant

    """

    def select(self):
        """ select based on n_constant value

        :return: GaussianHMM object
        """
        best_num_components = self.n_constant
        return self.base_model(best_num_components)


class SelectorBIC(ModelSelector):
    """ select the model with the lowest Bayesian Information Criterion(BIC) score

    http://www2.imm.dtu.dk/courses/02433/doc/ch6_slides.pdf
    Bayesian information criteria: BIC = -2 * logL + p * logN
    """

    def select(self):
        """ select the best model for self.this_word based on
        BIC score for n between self.min_n_components and self.max_n_components

        :return: GaussianHMM object
        """
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        bic_score = float("-inf")
        best_model = None
        for n in range(self.min_n_components, self.max_n_components+1):
            try:
                hmm_model = GaussianHMM(n_components=n, 
                                        covariance_type="diag", 
                                        n_iter=1000,
                                        random_state=self.random_state, 
                                        verbose=False).fit(self.X, self.lengths)

                logL = hmm_model.score(self.X, self.lengths)
                trans_matrix = hmm_model.transmat_
                p = n * (n-1) + 2 * n * len(self.X[0])
                score = -2 * logL + p * math.log(n)
                # print(score)
                if (score > bic_score):
                    bic_score = score
                    best_model = hmm_model
            except Exception as e:
                # print("error at step: " + str(n))
                # print(e)
                pass
        
        return best_model


class SelectorDIC(ModelSelector):
    ''' select best model based on Discriminative Information Criterion

    Biem, Alain. "A model selection criterion for classification: Application to hmm topology optimization."
    Document Analysis and Recognition, 2003. Proceedings. Seventh International Conference on. IEEE, 2003.
    http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.58.6208&rep=rep1&type=pdf
    DIC = log(P(X(i)) - 1/(M-1)SUM(log(P(X(all but i))
    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        best_score = float("-inf")
        best_model = None
        
        for n in range(self.min_n_components, self.max_n_components+1):
            try:
                hmm_model = GaussianHMM(n_components=n, 
                                        covariance_type="diag", 
                                        n_iter=1000,
                                        random_state=self.random_state, 
                                        verbose=False).fit(self.X, self.lengths)

                logL = hmm_model.score(self.X, self.lengths)
                other_scores = []

                for word in self.hwords:
                    word_x, word_lengths = self.hwords[word]
                    other_scores.append(hmm_model.score(word_x, word_lengths))
                
                score = logL - np.mean(other_scores)
                # print(score)
                if (score > best_score):
                    best_score = score
                    best_model = hmm_model
            except Exception as e:
                # print("error at step: " + str(n))
                # print(e)
                pass
        
        return best_model


class SelectorCV(ModelSelector):
    ''' select best model based on average log Likelihood of cross-validation folds

    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        best_score = float("-inf")
        best_model = None
        split_method = KFold(n_splits=2)

        for n in range(self.min_n_components, self.max_n_components+1):
            score = 0
            try:
                for cv_train_idx, cv_test_idx in split_method.split(self.sequences):
                    split_train_x, split_train_lengths = combine_sequences(cv_train_idx, self.sequences)
                    hmm_model = GaussianHMM(n_components=n, 
                                            covariance_type="diag", 
                                            n_iter=1000,
                                            random_state=self.random_state, 
                                            verbose=False).fit(split_train_x, split_train_lengths)

                    split_test_x, split_test_lengths = combine_sequences(cv_test_idx, self.sequences)
                    logL = hmm_model.score(split_test_x, split_test_lengths)
                    score = score + logL
                # print(score)
                if (score > best_score):
                    best_score = score
                    best_model = GaussianHMM(n_components=n, 
                                            covariance_type="diag", 
                                            n_iter=1000,
                                            random_state=self.random_state, 
                                            verbose=False).fit(self.X, self.lengths)
            except Exception as e:
                # print("error at step: " + str(n))
                # print(e)
                pass
        
        return best_model
