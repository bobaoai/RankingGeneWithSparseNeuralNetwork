import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import numpy as np

class NetworkPropagation():
    class PropagationNetwork(nn.Module):
        def __init__(self, sources, targets, nIter, nHiddens, nFeatures, pDropout, adaptiveEdgeWeights, alpha, adaptiveAlpha, gpu = gpu):
            super(NetworkPropagation.PropagationNetwork, self).__init__()
            self.pDropout = pDropout
            self.dropout = nn.Dropout(pDropout)
            self.nIter = nIter
            self.dense_ = nn.Linear(1, nHiddens)
            self.dense0 = nn.Linear(1, nHiddens)
            self.dense1 = nn.Linear(1, nHiddens)
            self.dense2 = nn.Linear(nHiddens, nFeatures)
            self.dense3 = nn.Linear(nFeatures, nHiddens)
            self.dense4 = nn.Linear(nHiddens, 1)
            if gpu:
				self.alpha = Variable(torch.FloatTensor([[alpha]]).cuda(), requires_grad = adaptiveAlpha)
            else:
				self.alpha = Variable(torch.FloatTensor([[alpha]]), requires_grad = adaptiveAlpha)
            #self.denseHS = nn.Linear(nFeatures, nHiddens)
            #self.denseHN = nn.Linear(nFeatures, nHiddens)
            #self.denseO = nn.Linear(nHiddens, nFeatures)
            
            #self.denseHS2 = nn.Linear(nFeatures, nHiddens)
            #self.denseHN2 = nn.Linear(nFeatures, nHiddens)
            #self.denseO2 = nn.Linear(nHiddens, nFeatures)
            
            #self.denseHS3 = nn.Linear(nFeatures, nHiddens)
            #self.denseHN3 = nn.Linear(nFeatures, nHiddens)
            #self.denseO3 = nn.Linear(nHiddens, nFeatures)
            
        def forward(self, x, sparse1, sparse2, edgeWeights):
            x = self.dropout(x)
            if self.training:
                x = x * (1 - self.pDropout)
            z = x
            for i in range(self.nIter):
                y = x
                x = self.dense2(F.sigmoid(self.dense1(x)))
                x = torch.matmul(sparse2, torch.matmul(sparse1, x) * edgeWeights)
                x = self.dense4(F.sigmoid(self.dense_(z) + self.dense0(y) + self.dense3(x))) + (1 - self.alpha) * z + self.alpha * torch.matmul(sparse2, torch.matmul(sparse1, y) * edgeWeights)
            
            #x = self.dense2(F.sigmoid(self.dense1(x)))
            #x = self.denseO(F.sigmoid(self.denseHS(x) + self.denseHN(torch.matmul(sparse2, torch.matmul(sparse1, x) * edgeWeights))))
            #x = self.denseO2(F.sigmoid(self.denseHS2(x) + self.denseHN2(torch.matmul(sparse2, torch.matmul(sparse1, x) * edgeWeights))))
            #x = self.denseO3(F.sigmoid(self.denseHS3(x) + self.denseHN3(torch.matmul(sparse2, torch.matmul(sparse1, x) * edgeWeights))))
            #x = self.dense4(F.sigmoid(self.dense3(x)))
            return x
        
    class Loss():
        def __init__(self):
            self.f = nn.BCELoss()
            
        def __call__(self, x, m1, m2, L):
            return self.f(F.sigmoid(torch.matmul(m1, x) - torch.matmul(m2, x)), L)
    
    def accuracy(self, x, m1, m2, L):
        return torch.sum(F.relu(torch.sign((torch.matmul(m1, x) - torch.matmul(m2, x)) * (L - 0.5)))) / L.size()[0]
        
    def __init__(self, values, sources, targets, optimizer, lr = 0.00001, nIter = 5, nHiddens = 2048, nFeatures = 16, gpu = True, pTeacher = 0.15, pHoldout = 0.05, pDropout = 0.05, valueCutoff = 4.6, pvalueCutoffFactor = 0.25, pDiffCutoff = 2.3, adaptiveEdgeWeights = False, alpha = 0.5, adaptiveAlpha = True):
        n = len(values)
        m = len(sources)
        self.nn = self.PropagationNetwork(sources, targets, nIter = nIter, nHiddens = nHiddens, nFeatures = nFeatures, pDropout = pDropout, adaptiveEdgeWeights = adaptiveEdgeWeights, alpha = alpha, adaptiveAlpha = adaptiveAlpha, gpu = gpu)
        y = torch.t(torch.FloatTensor([values])) + 1
        nHoldout = int(n * pHoldout)
        nTeacher = int(n * pTeacher)
        #totalMask = torch.FloatTensor([[0] if x < 1e-6 else [1] for x in values])
        totalMask = torch.FloatTensor([[1] if x < 1e-6 else [1] for x in values])
        mask = np.concatenate((np.ones((n - nHoldout, 1)), np.zeros((nHoldout, 1))))
        np.random.shuffle(mask)
        trainMask = torch.FloatTensor(mask.tolist()) * totalMask
        holdoutMask = torch.FloatTensor((np.ones((n, 1)) - mask).tolist()) * totalMask
        mask = np.concatenate((np.ones((nTeacher, 1)), np.zeros((n - nTeacher, 1))))
        np.random.shuffle(mask)
        teacherMask = torch.FloatTensor(mask.tolist()) * trainMask
        #self.y = Variable(y * holdoutMask, requires_grad = False)
        #self.trainMask = Variable(trainMask, requires_grad = False)
        #self.holdoutMask = Variable(holdoutMask, requires_grad = False)
        trainMask = trainMask.t().cpu().numpy().tolist()[0]
        holdoutMask = holdoutMask.t().cpu().numpy().tolist()[0]
        teacherMask = teacherMask.t().cpu().numpy().tolist()[0]
        print(len([i for i in range(n) if trainMask[i] == 1 and holdoutMask[i] == 1]))
        trainList = [i for i in range(n) if trainMask[i] == 1]
        holdoutList = [i for i in range(n) if holdoutMask[i] == 1]
        teacherList = [i for i in range(n) if teacherMask[i] == 1]
        print(len(trainList), len(holdoutList), len(teacherList))
        train1 = []
        train2 = []
        trainLabel = []
        sampleConunt = int(pTeacher * pTeacher * 0.05 * len(trainList))
        print(sampleConunt)
        for i in trainList:
            for k in np.random.randint(len(trainList), size = sampleConunt):
                j = trainList[k]
                if abs(values[i] - values[j]) > pDiffCutoff and (values[i] > valueCutoff or np.random.rand() < pvalueCutoffFactor) and (values[j] > valueCutoff or np.random.rand() < pvalueCutoffFactor):
                    train1.append(i)
                    train2.append(j)
                    trainLabel.append([1] if values[i] > values[j] else [0])
        print(len(train1))
        for i in teacherList:
            for j in teacherList:
                if abs(values[i] - values[j]) > pDiffCutoff and (values[i] > valueCutoff or np.random.rand() < pvalueCutoffFactor) and (values[j] > valueCutoff or np.random.rand() < pvalueCutoffFactor):
                    train1.append(i)
                    train2.append(j)
                    trainLabel.append([1] if values[i] > values[j] else [0])
        holdout1 = []
        holdout2 = []
        holdoutLabel = []
        for i in holdoutList:
            for j in holdoutList:
                if abs(values[i] - values[j]) > pDiffCutoff and (values[i] > valueCutoff or np.random.rand() < pvalueCutoffFactor) and (values[j] > valueCutoff or np.random.rand() < pvalueCutoffFactor):
                    holdout1.append(i)
                    holdout2.append(j)
                    holdoutLabel.append([1] if values[i] > values[j] else [0])
        print(len(train1), len(holdout1))
        print(len(trainLabel), len(holdoutLabel))
        
        self.lossFn = self.Loss()
        count = [0] * n
        for v in sources:
            count[v] += 1
        weights = [[1.0 / count[v]] for v in sources]
        
		if gpu:
            self.nn.cuda()
            self.y = Variable(y.cuda(), requires_grad = False)
		    self.x = Variable((y * trainMask * (1 - teacherMask)).cuda(), requires_grad = False)
            self.trainSparse1 = Variable(torch.sparse.FloatTensor(torch.LongTensor([list(range(len(train1))) + [0], train1 + [n - 1]]), torch.FloatTensor([1] * len(train1) + [0])).cuda(), requires_grad = False)
            self.trainSparse2 = Variable(torch.sparse.FloatTensor(torch.LongTensor([list(range(len(train1))) + [0], train2 + [n - 1]]), torch.FloatTensor([1] * len(train1) + [0])).cuda(), requires_grad = False)
            self.holdoutSparse1 = Variable(torch.sparse.FloatTensor(torch.LongTensor([list(range(len(holdout1))) + [0], holdout1 + [n - 1]]), torch.FloatTensor([1] * len(holdout1) + [0])).cuda(), requires_grad = False)
            self.holdoutSparse2 = Variable(torch.sparse.FloatTensor(torch.LongTensor([list(range(len(holdout1))) + [0], holdout2 + [n - 1]]), torch.FloatTensor([1] * len(holdout1) + [0])).cuda(), requires_grad = False)
            self.trainLabel = Variable(torch.FloatTensor(trainLabel).cuda(), requires_grad = False)
            self.holdoutLabel = Variable(torch.FloatTensor(holdoutLabel).cuda(), requires_grad = False)
            self.sparse1 = Variable(torch.sparse.FloatTensor(torch.LongTensor([range(m), sources]), torch.FloatTensor([1] * m)).cuda(), requires_grad = False)
            self.sparse2 = Variable(torch.sparse.FloatTensor(torch.LongTensor([targets, range(m)]), torch.FloatTensor([1] * m)).cuda(), requires_grad = False)
            self.edgeWeights = Variable(torch.FloatTensor(weights).cuda(), requires_grad = adaptiveEdgeWeights)#.expand(m, nFeatures)
        else:
            self.y = Variable(y, requires_grad = False)
		    self.x = Variable(y * trainMask * (1 - teacherMask), requires_grad = False)
            self.trainSparse1 = Variable(torch.sparse.FloatTensor(torch.LongTensor([list(range(len(train1))) + [0], train1 + [n - 1]]), torch.FloatTensor([1] * len(train1) + [0])), requires_grad = False)
            self.trainSparse2 = Variable(torch.sparse.FloatTensor(torch.LongTensor([list(range(len(train1))) + [0], train2 + [n - 1]]), torch.FloatTensor([1] * len(train1) + [0])), requires_grad = False)
            self.holdoutSparse1 = Variable(torch.sparse.FloatTensor(torch.LongTensor([list(range(len(holdout1))) + [0], holdout1 + [n - 1]]), torch.FloatTensor([1] * len(holdout1) + [0])), requires_grad = False)
            self.holdoutSparse2 = Variable(torch.sparse.FloatTensor(torch.LongTensor([list(range(len(holdout1))) + [0], holdout2 + [n - 1]]), torch.FloatTensor([1] * len(holdout1) + [0])), requires_grad = False)
            self.trainLabel = Variable(torch.FloatTensor(trainLabel), requires_grad = False)
            self.holdoutLabel = Variable(torch.FloatTensor(holdoutLabel), requires_grad = False)
            self.sparse1 = Variable(torch.sparse.FloatTensor(torch.LongTensor([range(m), sources]), torch.FloatTensor([1] * m)), requires_grad = False)
            self.sparse2 = Variable(torch.sparse.FloatTensor(torch.LongTensor([targets, range(m)]), torch.FloatTensor([1] * m)), requires_grad = False)
            self.edgeWeights = Variable(torch.FloatTensor(weights), requires_grad = adaptiveEdgeWeights)#.expand(m, nFeatures)
        
        print(self.sparse1.size(), self.sparse2.size(), self.edgeWeights.size())
        param = list(self.nn.parameters())
		if adaptiveEdgeWeights:
			param.append(adaptiveEdgeWeights)
		if adaptiveAlpha:
			param.append(adaptiveAlpha)
		self.optimizer = optimizer(param, lr = lr)
            
    def saveNetwork(self, path):
        torch.save(self.nn, path)
        
    def loadNetwork(self, path):
        self.nn = torch.load(path)
        
    def train(self, nIter, earlyStopThreshold = 50):
        self.nn.train()
        minIter = 0
        minLoss = 1e9
        for i in range(nIter):
            self.optimizer.zero_grad()
            output = self.nn(self.x, self.sparse1, self.sparse2, self.edgeWeights)
            loss = self.lossFn(output, self.trainSparse1, self.trainSparse2, self.trainLabel)
            trainLoss = loss.item()
            trainAccuracy = self.accuracy(output, self.trainSparse1, self.trainSparse2, self.trainLabel).item()
            loss.backward()
            self.optimizer.step()
            self.optimizer.zero_grad()
            loss = self.lossFn(output, self.holdoutSparse1, self.holdoutSparse2, self.holdoutLabel)
            holdoutLoss = loss.item()
            holdoutAccuracy = self.accuracy(output, self.holdoutSparse1, self.holdoutSparse2, self.holdoutLabel).item()
            print("Epoch =", i + 1)
            print("Training Loss =", trainLoss)
            print("Validation Loss =", holdoutLoss)
            print("Training Accuracy =", trainAccuracy)
            print("Validation Accuracy =", holdoutAccuracy)
            if holdoutLoss < minLoss:
                minLoss = holdoutLoss
                minIter = i
                self.saveNetwork("temp.pt")
            if i >= minIter + earlyStopThreshold:
                self.loadNetwork("temp.pt")
                break
            print("Min Validation Loss =", minLoss)
            print()
            
    
    def evaluate(self):
        self.nn.eval()
        output = self.nn(self.x, self.sparse1, self.sparse2, self.edgeWeights)
        print("Validation Loss =", self.lossFn(output, self.holdoutSparse1, self.holdoutSparse2, self.holdoutLabel).item())
        print("Validation Accuracy =", self.accuracy(output, self.holdoutSparse1, self.holdoutSparse2, self.holdoutLabel).item())
        output = None
        return (self.nn(self.y, self.sparse1, self.sparse2, self.edgeWeights).data).t().cpu().numpy().tolist()[0]
