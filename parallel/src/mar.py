from __future__ import print_function, division
import pickle
from pdb import set_trace
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import csv
from collections import Counter
from sklearn import svm
import matplotlib.pyplot as plt
import time
import os
from sklearn import preprocessing
from sklearn import linear_model


class Empty_Learner(object):
    def decision_function(self,matrix):
        return [0.0]*matrix.shape[0]

class MAR(object):
    def __init__(self):
        self.fea_num = 4000
        self.step = 10
        self.enough = 30
        self.kept=50
        self.atleast=100
        self.syn_thres = 0.8
        self.enable_est = False
        self.interval = 500000000


    def create(self,filename,partitions = 1):
        self.filename=filename
        self.name=self.filename.split(".")[0]
        self.flag=True
        self.hasLabel=True
        self.record={"x":[],"pos":[]}
        self.body={}
        self.est=[]
        self.last_pos=0
        self.last_neg=0
        self.record_est={"x":[],"semi":[],"sigmoid":[]}
        self.round = 0
        self.partitions = partitions


        try:
            ## if model already exists, load it ##
            return self.load()
        except:
            # print("Loading data")
            ## otherwise read from file ##
            try:
                self.loadfile()
                # print("Preprocessing")
                self.preprocess()
                # self.save()
            except:
                ## cannot find file in workspace ##
                print("Data file not found")
                self.flag=False
        return self

    ### Use previous knowledge, labeled only
    def create_old(self, filename):
        with open("../workspace/coded/" + str(filename), "r") as csvfile:
            content = [x for x in csv.reader(csvfile, delimiter=',')]
        fields = ["Document Title", "Abstract", "Year", "PDF Link", "code", "time"]
        header = content[0]
        ind0 = header.index("code")
        self.last_pos = len([c[ind0] for c in content[1:] if c[ind0] == "yes"])
        self.last_neg = len([c[ind0] for c in content[1:] if c[ind0] == "no"])
        for field in fields:
            ind = header.index(field)
            if field == "time":
                self.body[field].extend([float(c[ind]) for c in content[1:] if c[ind0] != "undetermined"])
            else:
                self.body[field].extend([c[ind] for c in content[1:] if c[ind0] != "undetermined"])
        try:
            ind = header.index("label")
            self.body["label"].extend([c[ind] for c in content[1:] if c[ind0]!="undetermined"])
        except:
            self.body["label"].extend([c[ind0] for c in content[1:] if c[ind0]!="undetermined"])

        self.preprocess()
        # self.save()

    ### Use previous knowledge, pos only
    def create_pos(self, filename):
        with open("../workspace/coded/" + str(filename), "r") as csvfile:
            content = [x for x in csv.reader(csvfile, delimiter=',')]
        fields = ["Document Title", "Abstract", "Year", "PDF Link", "code", "time"]
        header = content[0]
        ind0 = header.index("code")
        self.last_pos = len([c[ind0] for c in content[1:] if c[ind0] == "yes"])
        self.last_neg = 0
        for field in fields:
            ind = header.index(field)
            if field == "time":
                self.body[field].extend([float(c[ind]) for c in content[1:] if c[ind0] == "yes"])
            else:
                self.body[field].extend([c[ind] for c in content[1:] if c[ind0] == "yes"])
        try:
            ind = header.index("label")
            self.body["label"].extend([c[ind] for c in content[1:] if c[ind0]=="yes"])
        except:
            self.body["label"].extend([c[ind0] for c in content[1:] if c[ind0]=="yes"])

        self.preprocess()
        # self.save()


    def loadfile(self):
        with open("../workspace/data/" + str(self.filename), "r") as csvfile:
            content = [x for x in csv.reader(csvfile, delimiter=',')]
        fields = ["Document Title", "Abstract", "Year", "PDF Link"]
        header = content[0]
        for field in fields:
            ind = header.index(field)
            self.body[field] = [c[ind] for c in content[1:]]
        try:
            ind = header.index("label")
            self.body["label"] = [c[ind] for c in content[1:]]
        except:
            self.hasLabel=False
            self.body["label"] = ["unknown"] * (len(content) - 1)
        try:
            ind = header.index("code")
            self.body["code"] = [c[ind] for c in content[1:]]
        except:
            self.body["code"]=['undetermined']*(len(content) - 1)
        try:
            ind = header.index("time")
            self.body["time"] = [c[ind] for c in content[1:]]
        except:
            self.body["time"]=[0]*(len(content) - 1)
        try:
            ind = header.index("syn_error")
            self.body["syn_error"] = [c[ind] for c in content[1:]]
        except:
            self.body["syn_error"]=[0]*(len(content) - 1)
        try:
            ind = header.index("fixed")
            self.body["fixed"] = [c[ind] for c in content[1:]]
        except:
            self.body["fixed"]=[0]*(len(content) - 1)
        try:
            ind = header.index("count")
            self.body["count"] = [c[ind] for c in content[1:]]
        except:
            self.body["count"]=[0]*(len(content) - 1)
        try:
            ind = header.index("partition")
            self.body["partition"] = [c[ind] for c in content[1:]]
        except:
            self.body["partition"]=[np.random.randint(self.partitions) for c in content[1:]]

        self.parts = [set(np.where(np.array(self.body["partition"])==i)[0]) for i in xrange(self.partitions)]


        return
    

    def get_numbers(self):
        total = len(self.body["code"]) - self.last_pos - self.last_neg
        pos = Counter(self.body["code"])["yes"] - self.last_pos
        neg = Counter(self.body["code"])["no"] - self.last_neg
        try:
            tmp=self.record['x'][-1]
        except:
            tmp=-1
        if int(pos+neg)>tmp:
            self.record['x'].append(int(pos+neg))
            self.record['pos'].append(int(pos))
        self.pool = np.where(np.array(self.body['code']) == "undetermined")[0]
        self.labeled = list(set(range(len(self.body['code']))) - set(self.pool))
        return pos, neg, total

    def export(self):
        fields = ["Document Title", "Abstract", "Year", "PDF Link", "label", "code","time"]
        with open("../workspace/coded/" + str(self.name) + ".csv", "wb") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(fields)
            ## sort before export
            time_order = np.argsort(self.body["time"])[::-1]
            yes = [c for c in time_order if self.body["code"][c]=="yes"]
            no = [c for c in time_order if self.body["code"][c] == "no"]
            und = [c for c in time_order if self.body["code"][c] == "undetermined"]
            ##
            for ind in yes+no+und:
                csvwriter.writerow([self.body[field][ind] for field in fields])
        return

    def preprocess(self):
        ### Combine title and abstract for training ###########
        content = [self.body["Document Title"][index] + " " + self.body["Abstract"][index] for index in
                   xrange(len(self.body["Document Title"]))]
        #######################################################

        ### Feature selection by tfidf in order to keep vocabulary ###
        tfidfer = TfidfVectorizer(lowercase=True, stop_words="english", norm=None, use_idf=True, smooth_idf=False,
                                sublinear_tf=False,decode_error="ignore",max_features=4000)
        tfidfer.fit(content)
        self.voc = tfidfer.vocabulary_.keys()




        ##############################################################

        ### Term frequency as feature, L2 normalization ##########
        tfer = TfidfVectorizer(lowercase=True, stop_words="english", norm=u'l2', use_idf=False,
                        vocabulary=self.voc,decode_error="ignore")
        # tfer = TfidfVectorizer(lowercase=True, stop_words="english", norm=None, use_idf=False,
        #                 vocabulary=self.voc,decode_error="ignore")
        self.csr_mat=tfer.fit_transform(content)
        ########################################################
        return

    ## save model ##
    def save(self):
        with open("memory/"+str(self.name)+".pickle","w") as handle:
            pickle.dump(self,handle)

    ## load model ##
    def load(self):
        with open("memory/" + str(self.name) + ".pickle", "r") as handle:
            tmp = pickle.load(handle)
        return tmp



    def knee(self):
        y = self.record['pos'][-1]
        s = self.record['x'][-1]
        ratio = s/np.sqrt(y**2+s**2)
        per_best=-1
        best=0
        for i in range(len(self.record['x']))[::-1]:
            per = (self.record['pos'][i]-self.record['x'][i]*y/s)*ratio

            if per>per_best:
                best = i
                per_best=per

        rho = (s-self.record['x'][best])*self.record['pos'][best]/self.record['x'][best]/(1+y-self.record['pos'][best])
        # thres = 156-min((150,y))
        thres = 6
        if rho>=thres:
            return True
        else:
            return False

    def estimate_curve(self, decisions, reuse=False, num_neg=0):



        def prob_sample(probs):
            order = np.argsort(probs)[::-1]
            count = 0
            can = []
            sample = []
            for i, x in enumerate(probs[order]):
                count = count + x
                can.append(order[i])
                if count >= 1:
                    # sample.append(np.random.choice(can,1)[0])
                    sample.append(can[0])
                    count = 0
                    can = []
            return sample



        poses = np.where(np.array(self.body['code']) == "yes")[0]
        negs = np.where(np.array(self.body['code']) == "no")[0]

        poses = np.array(poses)[np.argsort(np.array(self.body['time'])[poses])[self.last_pos:]]
        negs = np.array(negs)[np.argsort(np.array(self.body['time'])[negs])[self.last_neg:]]

        ###############################################

        prob = np.array([[x] for x in decisions])


        y = np.array([1 if x == 'yes' else 0 for x in self.body['code']])
        y0 = np.copy(y)

        if len(poses) and reuse:
            all = list(set(poses) | set(negs) | set(self.pool))
        else:
            all = range(len(y))



        pos_num_last = Counter(y0)[1]

        lifes = 1
        life = lifes
        pos_num = Counter(y0)[1]

        while (True):
            C = Counter(y[all])[1]/ (num_neg)
            es = linear_model.LogisticRegression(penalty='l2', fit_intercept=True, C=C)

            es.fit(prob[all], y[all])
            pos_at = list(es.classes_).index(1)


            pre = es.predict_proba(prob[self.pool])[:, pos_at]


            y = np.copy(y0)

            sample = prob_sample(pre)
            for x in self.pool[sample]:
                y[x] = 1


            pos_num = Counter(y)[1]
            # crit=(pos_num-Counter(y0)[1])/pos_num
            # crit = (pos_num - pos_num_last) / pos_num_last
            # if crit<0.05:
            #     break
            if pos_num == pos_num_last:
                life = life - 1
                if life == 0:
                    break
            else:
                life = lifes
            pos_num_last = pos_num
        esty = pos_num - self.last_pos
        pre = es.predict_proba(prob)[:, pos_at]


        return esty, pre

    ## BM25 ##
    def BM25(self,query):
        if query[0]=='':
            self.bm = np.random.rand(len(self.body["Document Title"]))
            return

        b=0.75
        k1=1.5

        ### Combine title and abstract for training ###########
        content = [self.body["Document Title"][index] + " " + self.body["Abstract"][index] for index in
                   xrange(len(self.body["Document Title"]))]
        #######################################################

        ### Feature selection by tfidf in order to keep vocabulary ###

        tfidfer = TfidfVectorizer(lowercase=True, stop_words="english", norm=None, use_idf=False, smooth_idf=False,
                                  sublinear_tf=False, decode_error="ignore")
        tf = tfidfer.fit_transform(content)
        d_avg = np.mean(np.sum(tf, axis=1))
        score = {}
        for word in query:
            score[word]=[]
            try:
                id= tfidfer.vocabulary_[word]
            except:
                score[word]=[0]*len(content)
                continue
            df = sum([1 for wc in tf[:,id] if wc>0])
            idf = np.log((len(content)-df+0.5)/(df+0.5))
            for i in xrange(len(content)):
                score[word].append(idf*tf[i,id]/(tf[i,id]+k1*((1-b)+b*np.sum(tf[0],axis=1)[0,0]/d_avg)))
        self.bm = np.sum(score.values(),axis=0)

    def BM25_get(self):
        return self.pool[np.argsort(self.bm[self.pool])[::-1][:self.step]]

     ## Train model ##
    def train(self,pne=True,weighting=True):

        clf = svm.SVC(kernel='linear', probability=True, class_weight='balanced') if weighting else svm.SVC(kernel='linear', probability=True)
        poses = np.where(np.array(self.body['code']) == "yes")[0]
        negs = np.where(np.array(self.body['code']) == "no")[0]
        left = poses
        decayed = list(left) + list(negs)
        unlabeled = np.where(np.array(self.body['code']) == "undetermined")[0]
        try:
            unlabeled = np.random.choice(unlabeled,size=np.max((len(left),self.atleast)),replace=False)
        except:
            pass

        if not pne:
            unlabeled=[]

        labels=np.array([x if x!='undetermined' else 'no' for x in self.body['code']])
        all_neg=list(negs)+list(unlabeled)
        sample = list(decayed) + list(unlabeled)

        clf.fit(self.csr_mat[sample], labels[sample])


        ## aggressive undersampling ##
        if len(poses)>=self.enough:

            train_dist = clf.decision_function(self.csr_mat[all_neg])
            pos_at = list(clf.classes_).index("yes")
            if pos_at:
                train_dist=-train_dist
            negs_sel = np.argsort(train_dist)[::-1][:len(left)]
            sample = list(left) + list(np.array(all_neg)[negs_sel])
            clf.fit(self.csr_mat[sample], labels[sample])
        elif pne:
            train_dist = clf.decision_function(self.csr_mat[unlabeled])
            pos_at = list(clf.classes_).index("yes")
            if pos_at:
                train_dist = -train_dist
            unlabel_sel = np.argsort(train_dist)[::-1][:int(len(unlabeled) / 2)]
            sample = list(decayed) + list(np.array(unlabeled)[unlabel_sel])
            clf.fit(self.csr_mat[sample], labels[sample])

        ## correct errors with human-machine disagreements ##
        if self.round==self.interval:
            self.round=0
            susp, conf = self.susp(clf)
            return susp, conf, susp, conf
        else:
            self.round = self.round + 1
        #####################################################


        uncertain_id, uncertain_prob = self.uncertain(clf)
        certain_id, certain_prob = self.certain(clf)
        if self.enable_est:
            if self.last_pos>0 and len(poses)-self.last_pos>0:
                self.est_num, self.est = self.estimate_curve(clf.decision_function(self.csr_mat), reuse=True, num_neg=len(sample)-len(left))
            else:
                self.est_num, self.est = self.estimate_curve(clf.decision_function(self.csr_mat), reuse=False, num_neg=len(sample)-len(left))
            return uncertain_id, self.est[uncertain_id], certain_id, self.est[certain_id]
        else:
            return uncertain_id, uncertain_prob, certain_id, certain_prob

    ## Train model ##
    def train_para(self, pne=True,weighting=True):
        samples =int(self.step/self.partitions)
        clfs = [self.train_inner(i,pne=pne,weighting=weighting) for i in xrange(self.partitions)]

        all = np.array([[clf.decision_function(x)[0] for clf in clfs] for x in self.csr_mat])
        input = all[self.labeled]

        lgr = linear_model.LogisticRegression(penalty='l2', fit_intercept=True)

        lgr.fit(input,np.array(self.body['code'])[self.labeled])
        direction = 1
        if lgr.classes_[0]=='no':
            direction = -1
        uncertain_id = []
        certain_id = []
        for part in self.parts:
            what = np.array(list(part & set(self.pool)))
            dis = direction*lgr.decision_function(all[what])
            uncertain_order = np.argsort(np.abs(dis))[:samples]
            certain_order = np.argsort(dis)[:samples]
            uncertain_id.extend(what[uncertain_order])
            certain_id.extend(what[certain_order])

        return uncertain_id, uncertain_id, certain_id, certain_id

    ## Train model ##
    def train_inner(self, partition = 0, pne=True,weighting=True):

        clf = svm.SVC(kernel='linear', probability=True, class_weight='balanced') if weighting else svm.SVC(kernel='linear', probability=True)
        poses = np.array(list(set(np.where(np.array(self.body['code']) == "yes")[0]) & self.parts[partition]))
        negs = np.array(list(set(np.where(np.array(self.body['code']) == "no")[0])  & self.parts[partition]))

        if len(poses)==0:
            return Empty_Learner()

        left = poses
        decayed = list(left) + list(negs)
        unlabeled = np.array(list(set(np.where(np.array(self.body['code']) == "undetermined")[0])  & self.parts[partition]))
        try:
            unlabeled = np.random.choice(unlabeled,size=np.max((len(left),self.atleast)),replace=False)
        except:
            pass

        if not pne:
            unlabeled=[]

        labels=np.array([x if x!='undetermined' else 'no' for x in self.body['code']])
        all_neg=list(negs)+list(unlabeled)
        sample = list(decayed) + list(unlabeled)

        clf.fit(self.csr_mat[sample], labels[sample])


        ## aggressive undersampling ##
        if len(poses)>=self.enough:

            train_dist = clf.decision_function(self.csr_mat[all_neg])
            pos_at = list(clf.classes_).index("yes")
            if pos_at:
                train_dist=-train_dist
            negs_sel = np.argsort(train_dist)[::-1][:len(left)]
            sample = list(left) + list(np.array(all_neg)[negs_sel])
            clf.fit(self.csr_mat[sample], labels[sample])
        elif pne:
            train_dist = clf.decision_function(self.csr_mat[unlabeled])
            pos_at = list(clf.classes_).index("yes")
            if pos_at:
                train_dist = -train_dist
            unlabel_sel = np.argsort(train_dist)[::-1][:int(len(unlabeled) / 2)]
            sample = list(decayed) + list(np.array(unlabeled)[unlabel_sel])
            clf.fit(self.csr_mat[sample], labels[sample])

        return clf

    ## reuse
    def train_reuse(self,pne=True):
        pne=True
        clf = svm.SVC(kernel='linear', probability=True)
        poses = np.where(np.array(self.body['code']) == "yes")[0]
        negs = np.where(np.array(self.body['code']) == "no")[0]

        left = np.array(poses)[np.argsort(np.array(self.body['time'])[poses])[self.last_pos:]]
        negs = np.array(negs)[np.argsort(np.array(self.body['time'])[negs])[self.last_neg:]]

        if len(left)==0:
            return [], [], self.random(), []



        decayed = list(left) + list(negs)

        unlabeled = np.where(np.array(self.body['code']) == "undetermined")[0]
        try:
            unlabeled = np.random.choice(unlabeled, size=np.max((len(decayed), self.atleast)), replace=False)
        except:
            pass

        if not pne:
            unlabeled = []


        labels = np.array([x if x != 'undetermined' else 'no' for x in self.body['code']])
        all_neg = list(negs) + list(unlabeled)
        sample = list(decayed) + list(unlabeled)

        clf.fit(self.csr_mat[sample], labels[sample])
        ## aggressive undersampling ##
        if len(poses) >= self.enough:
            train_dist = clf.decision_function(self.csr_mat[all_neg])
            pos_at = list(clf.classes_).index("yes")
            if pos_at:
                train_dist=-train_dist
            negs_sel = np.argsort(train_dist)[::-1][:len(left)]
            sample = list(left) + list(np.array(all_neg)[negs_sel])
            clf.fit(self.csr_mat[sample], labels[sample])
        elif pne:
            train_dist = clf.decision_function(self.csr_mat[unlabeled])
            pos_at = list(clf.classes_).index("yes")
            if pos_at:
                train_dist = -train_dist
            unlabel_sel = np.argsort(train_dist)[::-1][:int(len(unlabeled) / 2)]
            sample = list(decayed) + list(np.array(unlabeled)[unlabel_sel])
            clf.fit(self.csr_mat[sample], labels[sample])

        uncertain_id, uncertain_prob = self.uncertain(clf)
        certain_id, certain_prob = self.certain(clf)

        if self.enable_est:
            self.est_num, self.est = self.estimate_curve(clf, reuse=False, num_neg=len(sample)-len(left))
            return uncertain_id, self.est[uncertain_id], certain_id, self.est[certain_id]
        else:
            return uncertain_id, uncertain_prob, certain_id, certain_prob



    ## Get certain ##
    def certain(self,clf):
        pos_at = list(clf.classes_).index("yes")
        prob = clf.predict_proba(self.csr_mat[self.pool])[:,pos_at]
        order = np.argsort(prob)[::-1][:self.step]
        return np.array(self.pool)[order],np.array(prob)[order]

    ## Get uncertain ##
    def uncertain(self,clf):
        pos_at = list(clf.classes_).index("yes")
        prob = clf.predict_proba(self.csr_mat[self.pool])[:, pos_at]
        train_dist = clf.decision_function(self.csr_mat[self.pool])
        order = np.argsort(np.abs(train_dist))[:self.step]  ## uncertainty sampling by distance to decision plane
        # order = np.argsort(np.abs(prob-0.5))[:self.step]    ## uncertainty sampling by prediction probability
        return np.array(self.pool)[order], np.array(prob)[order]

    ## Get random ##
    def random(self):
        return np.random.choice(self.pool,size=np.min((self.step,len(self.pool))),replace=False)

    ## Get one random ##
    def one_rand(self):
        pool_yes = filter(lambda x: self.body['label'][x]=='yes', range(len(self.body['label'])))
        return np.random.choice(pool_yes, size=1, replace=False)

    ## Format ##
    def format(self,id,prob=[]):
        result=[]
        for ind,i in enumerate(id):
            tmp = {key: self.body[key][i] for key in self.body}
            tmp["id"]=str(i)
            if prob!=[]:
                tmp["prob"]=prob[ind]
            result.append(tmp)
        return result

    ## Code candidate studies ##
    def code(self,id,label):
        self.body["code"][id] = label
        self.body["time"][id] = time.time()

    def code_error(self,id,error='none'):
        if error=='circle':
            self.code_circle(id, self.body['label'][id])
        elif error=='random':
            self.code_random(id, self.body['label'][id])
        elif error=='three':
            self.code_three(id, self.body['label'][id])
        else:
            self.code(id, self.body['label'][id])



    def code_three(self, id, label):
        self.code_random(id,label)
        self.code_random(id,label)
        if self.body['fixed'][id] == 0:
            self.code_random(id,label)

    def code_random(self,id,label):
        import random
        error_rate = 0.3
        if label=='yes':
            if random.random()<error_rate:
                new = 'no'
            else:
                new = 'yes'
        else:
            if random.random()<error_rate:
                new = 'yes'
            else:
                new = 'no'
        if new == self.body["code"][id]:
            self.body['fixed'][id]=1
        self.body["code"][id] = new
        self.body["time"][id] = time.time()
        self.body["count"][id] = self.body["count"][id] + 1

    ## Get suspecious codes
    def susp(self,clf):
        thres_pos = 1
        thres_neg = 0.5
        length_pos = 10
        length_neg = 10

        poses = np.where(np.array(self.body['code']) == "yes")[0]
        negs = np.where(np.array(self.body['code']) == "no")[0]
        poses = np.array(poses)[np.argsort(np.array(self.body['time'])[poses])[self.last_pos:]]
        negs = np.array(negs)[np.argsort(np.array(self.body['time'])[negs])[self.last_neg:]]

        poses = np.array(poses)[np.where(np.array(self.body['fixed'])[poses] == 0)[0]]
        negs = np.array(negs)[np.where(np.array(self.body['fixed'])[negs] == 0)[0]]


        pos_at = list(clf.classes_).index("yes")
        prob_pos = clf.predict_proba(self.csr_mat[poses])[:,pos_at]
        se_pos = np.argsort(prob_pos)[:length_pos]
        se_pos = [s for s in se_pos if prob_pos[s]<thres_pos]
        sel_pos = poses[se_pos]
        # print(np.array(self.body['label'])[sel_pos])

        neg_at = list(clf.classes_).index("no")
        prob_neg = clf.predict_proba(self.csr_mat[negs])[:,neg_at]
        se_neg = np.argsort(prob_neg)[:length_neg]
        se_neg = [s for s in se_neg if prob_neg[s]<thres_neg]
        sel_neg = negs[se_neg]
        # print(np.array(self.body['label'])[sel_neg])


        return sel_pos.tolist() + sel_neg.tolist(), prob_pos[se_pos].tolist() + prob_neg[se_neg].tolist()


    ## Plot ##
    def plot(self):
        font = {'family': 'normal',
                'weight': 'bold',
                'size': 20}

        plt.rc('font', **font)
        paras = {'lines.linewidth': 5, 'legend.fontsize': 20, 'axes.labelsize': 30, 'legend.frameon': False,
                 'figure.autolayout': True, 'figure.figsize': (16, 8)}

        plt.rcParams.update(paras)

        fig = plt.figure()
        plt.plot(self.record['x'], self.record["pos"])
        ### estimation ####
        if Counter(self.body['code'])['yes']>=self.enough:
            est=self.est2[self.pool]
            order=np.argsort(est)[::-1]
            xx=[self.record["x"][-1]]
            yy=[self.record["pos"][-1]]
            for x in xrange(int(len(order)/self.step)):
                delta = sum(est[order[x*self.step:(x+1)*self.step]])
                if delta>=0.1:
                    yy.append(yy[-1]+delta)
                    xx.append(xx[-1]+self.step)
                else:
                    break
            plt.plot(xx, yy, "-.")
        ####################
        plt.ylabel("Relevant Found")
        plt.xlabel("Documents Reviewed")
        name=self.name+ "_" + str(int(time.time()))+".png"

        dir = "./static/image"
        for file in os.listdir(dir):
            os.remove(os.path.join(dir, file))

        plt.savefig("./static/image/" + name)
        plt.close(fig)
        return name

    def get_allpos(self):
        return len([1 for c in self.body["label"] if c=="yes"])-self.last_pos

    ## Restart ##
    def restart(self):
        try:
            os.remove("./memory/"+self.name+".pickle")
        except:
            pass

    ## Get missed relevant docs ##
    def get_rest(self):
        rest=[x for x in xrange(len(self.body['label'])) if self.body['label'][x]=='yes' and self.body['code'][x]!='yes']
        rests={}
        # fields = ["Document Title", "Abstract", "Year", "PDF Link"]
        fields = ["Document Title"]
        for r in rest:
            rests[r]={}
            for f in fields:
                rests[r][f]=self.body[f][r]
        set_trace()
        return rests

    def cache_est(self):
        est = self.est[self.pool]
        order = np.argsort(est)[::-1]
        xx = [self.record["x"][-1]]
        yy = [self.record["pos"][-1]]
        for x in xrange(int(len(order) / self.step)):
            delta = sum(est[order[x * self.step:(x + 1) * self.step]])
            if delta >= 0.1:
                yy.append(yy[-1] + delta)
                xx.append(xx[-1] + self.step)
            else:
                break
        self.xx=xx
        self.yy=yy

        est = self.est2[self.pool]
        order = np.argsort(est)[::-1]
        xx2 = [self.record["x"][-1]]
        yy2 = [self.record["pos"][-1]]
        for x in xrange(int(len(order) / self.step)):
            delta = sum(est[order[x * self.step:(x + 1) * self.step]])
            if delta >= 0.1:
                yy2.append(yy2[-1] + delta)
                xx2.append(xx2[-1] + self.step)
            else:
                break
        self.xx2 = xx2
        self.yy2 = yy2