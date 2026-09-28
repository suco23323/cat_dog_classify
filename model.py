import torch
from torchsummary import summary
from torch import nn

# 定义残差块
class residual(nn.Module):
    def __init__(self,in_channels,out_channels,stride=1,use1x1=False):
        super(residual, self).__init__()
        self.residual_block=nn.Sequential(nn.Conv2d(in_channels=in_channels,out_channels=out_channels,kernel_size=3,stride=stride,padding=1),
                                          nn.BatchNorm2d(out_channels),
                                          nn.ReLU(),
                                          nn.Conv2d(in_channels=out_channels,out_channels=out_channels,kernel_size=3,stride=1,padding=1),
                                          nn.BatchNorm2d(out_channels))

        self.relu=nn.ReLU()

        if use1x1==True:
            self.conv=nn.Conv2d(in_channels=in_channels,out_channels=out_channels,kernel_size=1,stride=stride)
        else:
            self.conv=None

    def forward(self,x):
        y=self.residual_block(x)
        shortcut = x

        if self.conv is not None:
            shortcut = self.conv(x)
        y = y + shortcut
        y=self.relu(y)

        return y

class ResNet(nn.Module):
    def __init__(self,residual):
        super(ResNet, self).__init__()
        self.block1=nn.Sequential(nn.Conv2d(in_channels=3,out_channels=64,kernel_size=7,stride=2,padding=3),
                                  nn.BatchNorm2d(num_features=64),
                                  nn.ReLU(),
                                  nn.MaxPool2d(kernel_size=3,stride=2,padding=1))

        self.block2=nn.Sequential(residual(64,64,stride=1,use1x1=False),
                                  residual(64,64,stride=1,use1x1=False))

        self.block3=nn.Sequential(residual(64,128,stride=2,use1x1=True),
                                  residual(128,128,stride=1,use1x1=False))

        self.block4=nn.Sequential(residual(128,256,stride=2,use1x1=True),
                                  residual(256,256,stride=1,use1x1=False))

        self.block5=nn.Sequential(residual(256,512,stride=2,use1x1=True),
                                  residual(512,512,stride=1,use1x1=False))

        self.block6 =nn.Sequential(nn.AdaptiveAvgPool2d((1,1)),
                                   nn.Flatten(),
                                   nn.Linear(512,2))
    def forward(self,x):
        x=self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = self.block5(x)
        x = self.block6(x)

        return x

if __name__=='__main__':
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model=ResNet(residual).to(device)
    print(summary(model, (1, 224, 224)))