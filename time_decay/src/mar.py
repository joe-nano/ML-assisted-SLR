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

class MAR(object):
    def __init__(self):
        self.fea_num = 4000
        self.step = 10
        self.enough = 30
        self.keep = 50


    def create(self,filename):
        self.filename=filename
        self.name=self.filename.split(".")[0]
        self.flag=True
        self.hasLabel=True
        self.record={"x":[],"pos":[]}
        self.body={}
        self.est_num=[]
        self.lastprob=0
        self.offset=0.5
        self.interval=3
        self.buffer=[]

        try:
            ## if model already exists, load it ##
            return self.load()
        except:
            ## otherwise read from file ##
            try:
                self.loadfile()
                self.preprocess()
                self.save()
            except:
                ## cannot find file in workspace ##
                self.flag=False
        return self

    def create_UPDATE(self,filename,old):
        self.filename=filename
        self.name=self.filename.split(".")[0]
        self.flag=True
        self.hasLabel=True
        self.record={"x":[],"pos":[]}
        self.body={}
        self.est_num=[]
        self.lastprob=0
        self.offset=0.5
        self.interval=3
        self.buffer=[]

        try:
            ## if model already exists, load it ##
            return self.load()
        except:
            ## otherwise read from file ##
            try:
                self.loadfile()
                self.loadold(old)
                self.preprocess()
                self.save()
            except:
                ## cannot find file in workspace ##
                self.flag=False
        return self

    def create_UPDATE_ALL(self,filename,old):
        self.filename=filename
        self.name=self.filename.split(".")[0]
        self.flag=True
        self.hasLabel=True
        self.record={"x":[],"pos":[]}
        self.body={}
        self.est_num=[]
        self.lastprob=0
        self.offset=0.5
        self.interval=3
        self.buffer=[]

        try:
            ## if model already exists, load it ##
            return self.load()
        except:
            ## otherwise read from file ##
            try:
                self.loadfile()
                self.loadold_all(old)
                self.preprocess()
                self.save()
            except:
                ## cannot find file in workspace ##
                self.flag=False
        return self


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
            self.body["code"] = np.array([c[ind] for c in content[1:]])
        except:
            self.body["code"]= np.array(['undetermined']*(len(content) - 1))
        try:
            ind = header.index("decay")
            self.body["decay"] = np.array([c[ind] for c in content[1:]])
        except:
            self.body["decay"]= np.array([-1]*(len(content) - 1))

        self.num = len(content) - 1
        return

    ## for Partial UPDATE
    def loadold(self,old):
        with open("../workspace/coded/" + str(old), "r") as csvfile:
            content = [x for x in csv.reader(csvfile, delimiter=',')]
        fields = content[0]
        self.body['code']=self.body['code'].tolist()
        for x in content[1:]:
            code_ind = content[0].index("code")
            if x[code_ind]!="undetermined":
                for ind,field in enumerate(fields):
                    self.body[field].append(x[ind])
        self.body['code']=np.array(self.body['code'])

    ## for Whole UPDATE
    def loadold_all(self,old):
        with open("../workspace/coded/" + str(old), "r") as csvfile:
            content = [x for x in csv.reader(csvfile, delimiter=',')]
        fields = content[0]
        self.body['code']=self.body['code'].tolist()
        for x in content[1:]:
            for ind,field in enumerate(fields):
                self.body[field].append(x[ind])
        self.body['code']=np.array(self.body['code'])

    ## essential to be done before each training
    def get_numbers(self):
        total = self.num
        pos = Counter(self.body["code"][:self.num])["yes"]
        neg = Counter(self.body["code"][:self.num])["no"]
        try:
            tmp=self.record['x'][-1]
        except:
            tmp=-1
        if int(pos+neg)>tmp:
            self.record['x'].append(int(pos+neg))
            self.record['pos'].append(int(pos))
        tmp = np.where(self.body['code'] == "undetermined")[0]
        self.pool = np.where(self.body['code'][:self.num] == "undetermined")[0]
        self.labeled = list(set(range(len(self.body['code']))) - set(tmp))

        return pos, neg, total

    def get_allpos(self):
        return Counter(self.body["label"][:self.num])["yes"]

    ## export csv file to /workspace/coded/
    def export(self):
        fields = self.body.keys()
        with open("../workspace/coded/" + str(self.name) + ".csv", "wb") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(fields)
            for ind in xrange(len(self.body["code"])):
                csvwriter.writerow([self.body[field][ind] for field in fields])
        return

    def split_data(self,year):
        fields = ["Document Title", "Abstract", "Year", "PDF Link", "label", "code"]
        with open("../workspace/coded/" + str(self.name) +str(year)+ "-.csv", "wb") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(fields)
            for ind in xrange(len(self.body["code"])):
                if int(self.body['Year'][ind])<= int(year):
                    csvwriter.writerow([self.body[field][ind] for field in fields])
        with open("../workspace/coded/" + str(self.name) +str(year)+ "+.csv", "wb") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(fields)
            for ind in xrange(len(self.body["code"])):
                if int(self.body['Year'][ind])> int(year):
                    csvwriter.writerow([self.body[field][ind] for field in fields])
        return

    ## preprocess data, stemming+stopwords removal+feature selection+featurization
    def preprocess(self):
        ### Combine title and abstract for training ###########
        content = [self.body["Document Title"][index] + " " + self.body["Abstract"][index] for index in
                   xrange(len(self.body["Document Title"]))]
        #######################################################
        ### Feature selection by tfidf in order to keep vocabulary ###
        tfidfer = TfidfVectorizer(lowercase=True, stop_words="english", norm=None, use_idf=True, smooth_idf=False,
                                sublinear_tf=False,decode_error="ignore")
        tfidf = tfidfer.fit_transform(content)
        weight = tfidf.sum(axis=0).tolist()[0]
        kept = np.argsort(weight)[-self.fea_num:]
        self.voc = np.array(tfidfer.vocabulary_.keys())[np.argsort(tfidfer.vocabulary_.values())][kept]
        ##############################################################

        ### Term frequency as feature, L2 normalization ##########
        tfer = TfidfVectorizer(lowercase=True, stop_words="english", norm=u'l2', use_idf=False,
                        vocabulary=self.voc,decode_error="ignore")
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

    def estimate_curve(self,clf):
        ## estimate ##
        # self.est_num=Counter(clf.predict(self.csr_mat[self.pool]))["yes"]
        pos_at = list(clf.classes_).index("yes")
        prob = clf.predict_proba(self.csr_mat[self.pool])[:, pos_at]
        order = np.argsort(prob)[::-1]
        tmp = [x for x in np.array(prob)[order] if x > self.offset]

        ind = 0
        sum_tmp = 0
        self.est_num = []
        while True:
            tmp_x = tmp[ind * self.step:(ind + 1) * self.step]
            if len(tmp_x) == 0:
                break
            sum_tmp = sum_tmp + sum(tmp_x) - self.offset * len(tmp_x)
            self.est_num.append(sum_tmp)
            ind = ind + 1
            ##############
        try:
            self.lastprob = np.mean(clf.predict_proba(self.csr_mat[self.buffer])[:,pos_at])
            # self.lastprob = np.mean(np.array(prob)[order][:self.step])
        except:
            pass

    ## Train model ##
    def train(self):
        clf = svm.SVC(kernel='linear', probability=True)
        poses = np.where(self.body['code'] == "yes")[0]
        negs = np.where(self.body['code'] == "no")[0]
        clf.fit(self.csr_mat[self.labeled], self.body['code'][self.labeled])
        ## aggressive undersampling ##
        if len(poses)>=self.enough:

            train_dist = clf.decision_function(self.csr_mat[negs])
            negs_sel = np.argsort(np.abs(train_dist))[::-1][:len(poses)]
            sample = poses.tolist() + negs[negs_sel].tolist()
            clf.fit(self.csr_mat[sample], self.body['code'][sample])
            self.estimate_curve(clf)

        uncertain_id, uncertain_prob = self.uncertain(clf)
        certain_id, certain_prob = self.certain(clf)
        return uncertain_id, uncertain_prob, certain_id, certain_prob

    ## Train decay_keep model ##
    def train_decay_keep(self):
        clf = svm.SVC(kernel='linear', probability=True)
        # poses = np.where(self.body['code'] == "yes")[0]
        negs = np.where(self.body['code'] == "no")[0]

        ## decay_keep model
        poses = [i for i, x in enumerate(self.body["decay"]) if x>=0][:self.keep]
        self.labeled = list(negs)+poses

        clf.fit(self.csr_mat[self.labeled], self.body['code'][self.labeled])
        ## aggressive undersampling ##
        if len(poses)>=self.enough:

            train_dist = clf.decision_function(self.csr_mat[negs])
            negs_sel = np.argsort(np.abs(train_dist))[::-1][:len(poses)]
            sample = list(poses) + list(negs[negs_sel])
            clf.fit(self.csr_mat[sample], self.body['code'][sample])
            self.estimate_curve(clf)

        uncertain_id, uncertain_prob = self.uncertain(clf)
        certain_id, certain_prob = self.certain(clf)
        return uncertain_id, uncertain_prob, certain_id, certain_prob

    ## Train decay model ##
    def train_decay(self):
        clf = svm.SVC(kernel='linear', probability=True)
        poses = np.where(self.body['code'] == "yes")[0]
        negs = np.where(self.body['code'] == "no")[0]

        ## decay model
        offset = self.get_decay()-self.keep
        decays = [[i]*(x-offset) for i, x in enumerate(self.body["decay"]) if x>=0 and x-offset>0]
        decays = [item for sublist in decays for item in sublist]
        self.labeled = list(negs)+decays

        clf.fit(self.csr_mat[self.labeled], self.body['code'][self.labeled])
        ## aggressive undersampling ##
        if len(poses)>=self.enough:

            train_dist = clf.decision_function(self.csr_mat[negs])
            negs_sel = np.argsort(np.abs(train_dist))[::-1][:len(decays)]
            sample = decays + list(negs[negs_sel])
            clf.fit(self.csr_mat[sample], self.body['code'][sample])
            self.estimate_curve(clf)

        uncertain_id, uncertain_prob = self.uncertain(clf)
        certain_id, certain_prob = self.certain(clf)
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

    ## Reuse Model ##
    def reuse(self,model):
        order = np.argsort((model['w']*self.csr_mat[self.pool].transpose()).toarray()[0])
        if model['pos_at'] == 1:
            order=order[::-1]
        can=[self.pool[i] for i in order[:int(self.step/2)]]
        num=self.step-int(self.step/2)
        can.extend([self.pool[order[-int(i*len(order)/num+1)]] for i in xrange(num)])
        return np.array(can)

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
        self.buffer.append(id)
        self.buffer=self.buffer[-self.step * self.interval:]
        self.body["code"][id]=label
        if label=="yes":
            self.body["decay"][id]=self.get_decay()+1

    ## Get latest decay
    def get_decay(self):
        return np.max(self.body["decay"])

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
        if len(self.est_num)>0 and self.lastprob>self.offset:
            der = (self.record["pos"][-1]-self.record["pos"][-1-self.interval])/(self.record["x"][-1]-self.record["x"][-1-self.interval])
            xx=np.array(range(len(self.est_num)+1))
            yy=map(int,np.array(self.est_num)*der/(self.lastprob-self.offset)+self.record["pos"][-1])
            # yy = map(int, np.array(self.est_num) + (der - self.lastprob)*xx[1:]*self.step + self.record["pos"][-1])
            yy=[self.record["pos"][-1]]+list(yy)
            xx=xx*self.step+self.record["x"][-1]
            plt.plot(xx, yy, "-.")
        ####################
        plt.ylabel("Relevant Found")
        plt.xlabel("Documents Reviewed")
        name=self.name+ "_" + str(int(time.time()))+".png"

        dir = "./static/image"
        for file in os.listdir(dir):
            os.remove(os.path.join(dir,file))

        plt.savefig("./static/image/" + name)
        plt.close(fig)
        return name

    ## Restart ##
    def restart(self):
        os.remove("./memory/"+self.name+".pickle")

    ## Train model ##
    def get_clf(self):
        clf = svm.SVC(kernel='linear', probability=True)
        poses = np.where(self.body['code'] == "yes")[0]
        negs = np.where(self.body['code'] == "no")[0]
        clf.fit(self.csr_mat[self.labeled], self.body['code'][self.labeled])
        ## aggressive undersampling ##
        if len(poses)>=self.enough:

            train_dist = clf.decision_function(self.csr_mat[negs])
            negs_sel = np.argsort(np.abs(train_dist))[::-1][:len(poses)]
            sample = poses.tolist() + negs[negs_sel].tolist()
            clf.fit(self.csr_mat[sample], self.body['code'][sample])
        return clf

    ## set enough
    def set_enough(self,enough):
        self.enough=enough