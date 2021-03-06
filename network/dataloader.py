import numpy as np
import math

from .distances import *
from .mappings import *

from tqdm import tqdm
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from ripser import ripser
from persim import plot_diagrams

#Loading data from a specific scene

class DL:
    def __init__(self,scene,input_frames,input_agents):
        self.frame_interval = scene['frame_index_interval']
        self.scene = scene
        self.frames = input_frames
        self.agents = input_agents
        
        self.dataframe = self.getData()

    def getData(self):        
        key_frames = self.frames[self.scene['frame_index_interval'][0]:self.scene['frame_index_interval'][1]]
        key_agents = self.agents[key_frames[0]['agent_index_interval'][0]:key_frames[-1]['agent_index_interval'][1]]
        
        key_frames = [map_frame_array_to_dict(f) for f in key_frames]
        key_agents = [map_agent_array_to_dict(a) for a in key_agents]   
        
        start_agent_index = key_frames[0]['agent_index_interval'][0]
        num_frames = self.scene['frame_index_interval'][1]-self.scene['frame_index_interval'][0]
        
        ret_agents = np.ones((4,3000,num_frames,2))
        ret_agents[1] = ret_agents[1]*-1 #vels
        ret_agents[2] = ret_agents[2]*2 #yaws
        ret_agents[3] = ret_agents[3]*-1 #tags
        
        for frame_num in range(num_frames):
            frame = key_frames[frame_num]
            ret_agents[0][0][frame_num] = frame['ego_translation'][:2]
            ret_agents[2][0][frame_num][0] = math.acos(frame['ego_rotation'][0][0])
            for j in range(frame['agent_index_interval'][0]-start_agent_index,frame['agent_index_interval'][1]-start_agent_index):
                agent = key_agents[j]
                ret_agents[0][agent['track_id']][frame_num] = agent['centroid']
                ret_agents[1][agent['track_id']][frame_num] = agent['velocity']
                ret_agents[2][agent['track_id']][frame_num][0] = agent['yaw']
                ret_agents[3][agent['track_id']][frame_num][0] = j
                
        ret_agents = map_ret_to_dict(ret_agents)
        return ret_agents

    def findPathMatch(self,start,end):
        ret_agents = self.dataframe
        ret = []
        coords = ret_agents['coordinates']
        for agent_num in range(len(coords)):
            agent = coords[agent_num]
            if len(getWithout(agent,1)) > 20:
                match = [False,False]
                for pos in agent:
                    if sum((pos - start)**2) < 10:
                        match[0] = True
                    if sum((pos - end)**2) < 10:
                        match[1] = True
                        break
                if sum(match) == 2:
                    ret.append(ret_agents[:,agent_num,:,:])
        return ret  

    def getAgentDensities(self,agent_num,k,t):
        tags = self.dataframe['tags']
        if t[0] == 0:
            densities = getDensitiesAll(self,agent_num)
        else:
            densities = getDensitiesMoving(self,agent_num)
        if t[1] == 0:
            ret = returnDensitiesDistances(self,densities,k)
        else:
            ret = returnDensitiesRadius(self,densities,k)
        return ret

    def getDensitiesAll(self,agent_num):
        tags = self.dataframe['tags']
        pos = tags[agent_num]
        densities = []
        for frame_num in range(len(pos)):
            if pos[frame_num] == -1:
                densities.append([0])
                continue
            temp = np.zeros((self.frames[frame_num]['agent_index_interval'][1]-self.frames[frame_num]['agent_index_interval'][0]))
            for agent_count,agent_index in enumerate(range(self.frames[frame_num]['agent_index_interval'][0],self.frames[frame_num]['agent_index_interval'][1])):
                #print(distance_from_edge(agents[agent_index],agents[pos[frame_num]]))
                #print(distance_from_center(agents[agent_index],agents[pos[frame_num]]))
                temp[agent_count] = distance_from_edge(self.agents[agent_index],self.agents[pos[frame_num]])
            densities.append(temp)
        return np.array(densities,dtype = object)

    def getDensitiesMoving(self,agent_num):
        tags = self.dataframe['tags']
        pos = tags[agent_num]
        densities = []
        for frame_num in range(len(pos)):
            if pos[frame_num] == -1:
                densities.append([0])
                continue
            temp = np.zeros((self.frames[frame_num]['agent_index_interval'][1]-self.frames[frame_num]['agent_index_interval'][0]))
            for agent_count,agent_index in enumerate(range(self.frames[frame_num]['agent_index_interval'][0],self.frames[frame_num]['agent_index_interval'][1])):
                if math.hypot(self.agents[agent_index]['velocity'][0],self.agents[agent_index]['velocity'][1]) > 1:
                    temp[agent_count] = distance_from_edge(self.agents[agent_index],self.agents[pos[frame_num]])
                else:
                    temp[agent_count] = 1000
            densities.append(temp)
        return np.array(densities,dtype = object)

    def returnDensitiesDistances(self,densities,k):
        dist_densities = -1 * np.ones((len(densities)))
        for frame_num in range(len(densities)):
            if len(densities[frame_num])==1:
                continue
            dist_densities[frame_num] = np.sort(densities[frame_num])[k+1]
        return dist_densities

    def returnDensitiesRadius(self,densities,k):
        dist_densities = -1 * np.ones((len(densities)))
        for frame_num in range(len(densities)):
            if len(densities[frame_num])==1:
                continue
            dist_densities[frame_num] = (densities[frame_num]<k).sum()
        return dist_densities

    

    def plotAgentPos(self,agent_num):
        coords = self.dataframe['coordinates']
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        Axes3D.scatter(ax,getWithout(coords[agent_num][:,0],1),getWithout(coords[agent_num][:,1],1),zs = np.arange(len(coords[agent_num]))[coords[agent_num][:,0]!=1],s=3)
        plt.show()
        
    def plotAgentVel(self,agent_num):
        vels = self.dataframe['velocity']
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        Axes3D.scatter(ax,getWithout(vels[agent_num][:,0],-1),getWithout(vels[agent_num][:,1],-1),zs = np.arange(len(vels[agent_num]))[vels[agent_num][:,0]!=-1],s=3)
        plt.show()
        
    def plotAgentYaw(self,agent_num):
        yaws = self.data['yaws']
        fig = plt.figure()
        ax = plt.subplot()
        ax.scatter(np.arange(len(yaws[agent_num]))[yaws[agent_num][:,0]!=2],getWithout(yaws[agent_num][:,0],2))
        plt.show()
        
    def plotAgentSpeed(self,agent_num):
        vels = self.dataframe['velocity']
        fig = plt.figure()
        ax = plt.subplot()
        ax.scatter(np.arange(len(vels[agent_num]))[vels[agent_num][:,0]!=-1],getWithout((vels[agent_num][:,0]**2+vels[agent_num][:,1]**2)**.5,math.sqrt(2)))

    def plotAgentDensity(agent_density):
        fig = plt.figure()
        ax = plt.subplot()
        ax.scatter(np.arange(len(agent_density))[agent_density!=-1],getWithout(agent_density,-1))
