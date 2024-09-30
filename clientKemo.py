from collections import OrderedDict
import flwr as fl
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from Old_train import train, valid
import warnings
from utils import *
from Network import *
import os
from torch.optim import SGD
import numpy as np
import random
class FedAvgClient(fl.client.NumPyClient):
    def __init__(self, net, train_loader, valid_loader, epoch, lossf, optimizer, DEVICE, trainF=train, validF=valid):
        super(FedAvgClient, self).__init__()
        self.net = net
        self.keys = net.state_dict().keys()
        self.train_loader = train_loader
        self.epoch = epoch
        self.lossf = lossf
        self.optim = optimizer
        self.DEVICE=DEVICE
        self.valid_loader= valid_loader
        self.train = trainF
        self.valid = validF
    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in self.net.state_dict().items()]

    def set_parameters(self, parameters):
        params_dict = zip(self.keys, parameters)
        state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
        self.net.load_state_dict(state_dict, strict=True)
    
    def fit(self, parameters, config):
        self.set_parameters(parameters)
        self.train(self.net, self.train_loader, None, self.epoch, self.lossf, self.optim, self.DEVICE, None)
        return self.get_parameters(config={}), len(self.train_loader), {}
        
    # def evaluate(self, parameters, config):
        # self.set_parameters(parameters)
        # history = self.valid(self.net, self.valid_loader, None, lossf=self.lossf, DEVICE=self.DEVICE)
        # return history["loss"], len(self.valid_loader), {key:value for key, value in history.items() if key != "loss" }
        # return 1.0, 0, {"accuracy":0.95}
    
if __name__ =="__main__":
    warnings.filterwarnings("ignore")
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    args = Federatedparser()
    
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.enabled = False
    
    valid_data = K_EMODataset("./data/e4_data/e4_data/valid", "./data/emotion_annotations/emotion_annotations/self_annotations")
    valid_loader = DataLoader(valid_data, batch_size=args.batch_size, shuffle=False, collate_fn= lambda x:x)
        
    train_data = K_EMODataset(f"./data/e4_data/e4_data/client{args.id}", "./data/emotion_annotations/emotion_annotations/self_annotations")
    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True, collate_fn= lambda x:x)
    
    
    net = K_emo_GRU(3, 4, 1)
    net.to(DEVICE)
    if args.pretrained is not None:
        net.load_state_dict(torch.load(args.pretrained))
    lossf = nn.BCEWithLogitsLoss()
    optimizer = SGD(net.parameters(), lr=1e-2)
    fl.client.start_client(server_address="[::]:8084", client= FedAvgClient(net, train_loader, valid_loader, args.epoch, lossf, optimizer, DEVICE).to_client())
    