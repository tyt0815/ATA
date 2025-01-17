import argparse
import time
from collections import Counter

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets
from torchvision.transforms import ToTensor
import torchvision.models as models
import timm
from timm.data.constants import IMAGENET_DEFAULT_MEAN, IMAGENET_DEFAULT_STD

from ata.network.mlp import NeuralNetwork
from ata.data.dataset import OfflineDataset

from kornia.losses.focal import FocalLoss

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        type=str,
        default="efficientnetb0",
        choices=["efficientnetb0"]
    )
    parser.add_argument(
        '--sequence-len',
        type=int,
        default=60
    )
    parser.add_argument(
        '--train-path',
        type=str,
        default='BTC_Data2.csv'
    )
    parser.add_argument(
        '--test-path',
        type=str,
        default='BTC_Data3.csv'
    )
    
    return parser.parse_args()
    
def train(dataloader, model, loss_fn, optimizer, scheduler, device):
    size = len(dataloader.dataset)
    start = time.time()
    
    for batch, (X, y) in enumerate(dataloader):
        X, y = X.to(device), y.to(device)

        # 예측 오류 계산
        pred = model(X)
        loss = loss_fn(pred, y)

        # 역전파
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        if batch % 100 == 0:
            end = time.time()
            loss, current = loss.item(), (batch + 1) * len(X)
            print(f"loss: {loss:>7f}  [{current:>5d}/{size:>5d}]({end - start})")
            start = time.time()
        
def test(dataloader, model, loss_fn, device):
    print('############## Test ##############')
    size = len(dataloader.dataset)
    num_batches = len(dataloader)
    model.eval()
    test_loss, correct = 0, 0
    
    with torch.no_grad():
        for X, y in dataloader:
            X, y = X.to(device), y.to(device)
            pred = model(X)
            
            test_loss += loss_fn(pred, y).item()
            correct += (pred.argmax(1) == y).type(torch.float).sum().item()
    test_loss /= num_batches
    correct /= size
    print(f"Test Error: \n Accuracy: {(100*correct):>0.1f}%, Avg loss: {test_loss:>8f} \n")

if __name__ == '__main__':
    args = get_args()
    # 학습에 사용할 CPU나 GPU, MPS 장치를 얻습니다.
    device = (
        "cuda"
        if torch.cuda.is_available()
        else "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )
    print(f"Using {device} device")
    
    training_data = OfflineDataset(args.train_path, args.sequence_len)
    test_data = OfflineDataset(args.test_path, args.sequence_len)
    
    batch_size = 64

    # 데이터로더를 생성합니다.
    train_dataloader = DataLoader(training_data, batch_size=batch_size)
    test_dataloader = DataLoader(test_data, batch_size=batch_size)
    
    h = 0
    w = 0
    for X, y in test_dataloader:
        print(f"Shape of X [N, C, H, W]: {X.shape}")
        print(f"Shape of y: {y.shape} {y.dtype}")
        h = X.shape[2]
        w = X.shape[3]
        break 
    
    num_classes = 3
    
    model = models.efficientnet_b0(pretrained=False, num_classes = num_classes)
    model.features[0][0] = nn.Conv2d(1, model.features[0][0].out_channels, kernel_size=3, stride=2, padding=1, bias=False)
    
    # model = NeuralNetwork(input_size=h * w)
    
    model = model.to(device)
    print(model)
    
    loss_fn = nn.CrossEntropyLoss()
    # loss_fn = FocalLoss(alpha=0.25, gamma=5, reduction='sum')
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)
    
    epochs = 5
    for t in range(epochs):
        print(f"Epoch {t+1}\n-------------------------------")
        train(train_dataloader, model, loss_fn, optimizer, scheduler, device)
        test(test_dataloader, model, loss_fn, device)
    print("Done!")