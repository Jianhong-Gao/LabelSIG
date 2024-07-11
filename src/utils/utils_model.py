import torch
from torch.nn import Linear
import torch.nn.functional as F
import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv, global_mean_pool
import numpy as np
import matplotlib.pyplot as plt
def min_max_normalization(data):
    min_val = np.min(data)
    max_val = np.max(data)

    normalized_data = (data - min_val) / (max_val - min_val+1e-10)
    return normalized_data

def z_score_normalization(data):
    mean_val = np.mean(data)
    std_val = np.std(data)
    normalized_data = (data - mean_val) / (std_val+1e-10)
    return normalized_data

def apply_pre_transform_batch_data_graph(data_batch):
    """Applies pre-transform to all elements of a data batch."""
    for node in range(len(data_batch)):
        raw_data=data_batch[node]
        temp_data = torch.tensor(min_max_normalization(raw_data.numpy()), dtype=torch.float)
        data_batch[node] = temp_data
    return data_batch

def apply_pre_transform_batch_data(data_batch):
    """Applies pre-transform to all elements of a data batch."""
    for id_batch in range(len(data_batch)):
        data_channels=data_batch[id_batch]
        for channel in range(len(data_channels)):
            raw_data=data_batch[id_batch][channel]
            temp_data=torch.tensor(min_max_normalization(raw_data.numpy()), dtype=torch.float)
            data_batch[id_batch][channel]=temp_data
    return data_batch

class GCN(torch.nn.Module):
    def __init__(self, num_node_features, hidden_channels, num_classes,SEED = 12345,transform=False):
        super(GCN, self).__init__()
        self.transform=transform
        torch.manual_seed(SEED)
        self.conv1 = GCNConv(num_node_features, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.conv3 = GCNConv(hidden_channels, hidden_channels)
        self.lin = Linear(hidden_channels, num_classes)
    def forward(self, x, edge_index, batch):
        # channel_vis_graph(graph_data=x[0:10])
        if self.transform:
           x=apply_pre_transform_batch_data_graph(x)
           # channel_vis_graph(graph_data=x[0:10])
        x = F.relu(self.conv1(x, edge_index))
        x = F.relu(self.conv2(x, edge_index))
        x = self.conv3(x, edge_index)
        x = global_mean_pool(x, batch)
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.lin(x)
        return x

class TimeSeriesCNN(nn.Module):
    def __init__(self, input_length, num_classes,transform=False):
        super(TimeSeriesCNN, self).__init__()
        self.transform=transform
        # Assuming the input is of shape (batch_size, channels, input_length)
        # where channels could be 2 (one for voltage and one for current)
        self.conv1 = nn.Conv1d(in_channels=2, out_channels=64, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv1d(in_channels=64, out_channels=128, kernel_size=3, stride=1, padding=1)
        self.fc1 = nn.Linear(in_features=128*input_length, out_features=256)  # assuming we don't change the time series length
        self.fc2 = nn.Linear(in_features=256, out_features=num_classes)

    def forward(self, x):
        # channel_vis(x[0])
        if self.transform:
           x=apply_pre_transform_batch_data(x)
        # channel_vis(x[0])
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = x.view(x.size(0), -1)  # flatten the tensor
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

def channel_vis(channel_data):
    voltage=channel_data[0]
    current=channel_data[1]
    fig, ax1 = plt.subplots()
    ax1.plot(voltage, color='r')
    ax1.set_ylabel('Voltage(V)')
    ax2 = ax1.twinx()
    ax2.plot(current, color='b')
    ax2.set_ylabel('Current(A)')
    plt.subplots_adjust(left=0.1,right=0.85,top=0.9,bottom=0.1)
    plt.show()

def channel_vis_graph(graph_data,num_nodes=10):
    for i in range(int(num_nodes/2)):
        voltage=graph_data[i]
        current=graph_data[int(i+num_nodes/2)]
        fig, ax1 = plt.subplots()
        ax1.plot(voltage, color='r')
        ax1.set_ylabel('Voltage(V)')
        ax2 = ax1.twinx()
        ax2.plot(current, color='b')
        ax2.set_ylabel('Current(A)')
        plt.subplots_adjust(left=0.1,right=0.85,top=0.9,bottom=0.1)
        plt.show()