# -*- coding: utf-8 -*-
"""
Created on Thursday March 22 12:39:11 2018

@author: Tongli Zhang
Based on code from Derin Aksit
"""
import sys 
import os
sys.path.insert(0, os.path.abspath('../')) #Path to ConsumptionSaving folder
sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../../cstwMPC')) #Path to cstwMPC folder

import SetupParamsCSTWUncert as Params
from copy import deepcopy
from scipy.optimize import golden, brentq
from time import clock
import cstwMPC
import numpy as np

import matplotlib.pyplot as plt
import scipy as sp

#Chosse the folder to save the output graphs
Folder_path='C:\Personal\Research\Winter-Break-Project-2017\OneChapter'

# Set targets for K/Y and the Lorenz curve based on the data
lorenz_target = cstwMPC.getLorenzShares(Params.SCF_wealth,weights=Params.SCF_weights,percentiles=Params.percentiles_to_match)
lorenz_long_data = np.hstack((np.array(0.0),cstwMPC.getLorenzShares(Params.SCF_wealth,weights=Params.SCF_weights,percentiles=np.arange(0.01,1.0,0.01).tolist()),np.array(1.0)))
KY_target = 10.26

# Construct empty arrays for MPS and aggregate saving rate
MPS=[]
ASR=[]
AtoY=[]

# Do param-dist version if True, param-point if False
Params.do_param_dist=True

#search for spread_estimate and center estimate if true, use the given value if false
do_optimizing=False

# Define the agent type
BaselineType = cstwMPC.cstwMPCagent(**Params.init_infinite)

#Set benchmark values for std of permanent shock and transitory shock
BaselineType.PermShkStd = [(0.01*4/11)**0.5]
BaselineType.TranShkStd =[(0.01*4)**0.5]
cstwMPC.cstwMPCagent.updateIncomeProcess(BaselineType) # Crucial step for new PermShkStd value to be used 

# Estimate Beta distribution
BaselineType.AgeDstn = np.array(1.0)

# Make agent types for estimation   
EstimationAgentList = []
for n in range(Params.pref_type_count):
    EstimationAgentList.append(deepcopy(BaselineType))
        
# Give all the AgentTypes different seeds
for j in range(len(EstimationAgentList)):
    EstimationAgentList[j].seed = j
    
# Make an economy for the consumers to live in
EstimationEconomy = cstwMPC.cstwMPCmarket(**Params.init_market)
EstimationEconomy.agents = EstimationAgentList
EstimationEconomy.KYratioTarget = KY_target
EstimationEconomy.LorenzTarget = lorenz_target
EstimationEconomy.LorenzData = lorenz_long_data
EstimationEconomy.PopGroFac = Params.PopGroFac
EstimationEconomy.TypeWeight = [1.0]
EstimationEconomy.act_T = Params.T_sim_PY
EstimationEconomy.ignore_periods = Params.ignore_periods_PY

#center_pre=0.9727429241595354  #result under the calibration of the baseline model
#spread_pre=0.035829912170553285 #result under the calibration of the baseline model
center_pre=0.9869173152693166 #result under the calibration of the QE paper G=1.015
spread_pre=0.0110844191673392 #result under the calibration of the QE paper G=1.015
#center_pre=0.9855570905831315  #result under the calibration of the QE paper, G=1.04
#spread_pre=0.015510492348684882 #result under the calibration of the QE paper, G=1.04

param_range = [0.9,0.999] #The optimal beta when cstwMPC is run with beta-dist and PermShkStd = [(0.02*4/11)**0.5]
spread_range = [0.005,0.03] #The optimal nabla when cstwMPC is run with beta-dist and PermShkStd = [(0.02*4/11)**0.5]
if do_optimizing:
    if Params.do_param_dist:
        # Run the param-dist estimation
        paramDistObjective = lambda spread : cstwMPC.findLorenzDistanceAtTargetKY(
                                                        Economy = EstimationEconomy,
                                                        param_name = Params.param_name,
                                                        param_count = Params.pref_type_count,
                                                        center_range = param_range,
                                                        spread = spread,
                                                        dist_type = Params.dist_type)
        t_start = clock()
        spread_estimate = golden(paramDistObjective,brack=spread_range,tol=1e-4)
        center_estimate = EstimationEconomy.center_save
        t_end = clock()
    else:
        # Run the param-point estimation only
        paramPointObjective = lambda center : cstwMPC.getKYratioDifference(Economy = EstimationEconomy,
                                              param_name = Params.param_name,
                                              param_count = Params.pref_type_count,
                                              center = center,
                                              spread = 0.0,
                                              dist_type = Params.dist_type)
        t_start = clock()
        center_estimate = brentq(paramPointObjective,param_range[0],param_range[1],xtol=1e-6)
        spread_estimate = 0.0
        t_end = clock()
        
        print(spread_estimate)
        print('****************')
        print(center_estimate)
        print('****************')
else:
    center_estimate=center_pre
    spread_estimate=spread_pre

#Display statistics about the estimated model
EstimationEconomy.LorenzBool = True
EstimationEconomy.ManyStatsBool = True
EstimationEconomy.distributeParams(Params.param_name,Params.pref_type_count,center_estimate,spread_estimate,Params.dist_type)
EstimationEconomy.center_estimate = center_estimate
EstimationEconomy.spread_estimate = spread_estimate

#Calculate GIC of the most patient consumer
std_GIC=(np.arange(0.005,0.021,0.001)*4/11)**0.5
GIC_v=[]
R_GIC=BaselineType.Rfree*Params.LivPrb_i[0] #Interest rate we use to calculate GIC
for k in np.arange(0.005,0.021,0.001):
    print(k)    
    PermShkStd=[(k*4/11)**0.5]
    #calculate psi prime
    ShockSample=np.random.lognormal(0.0,PermShkStd,10000000)
    Inv_sample=1/ShockSample
    Ex_psi_inv=1/(np.mean(Inv_sample))
    Perm_Gro_em=Params.PermGroFac_i[0]*Params.PermGroFacAgg
    GIC=(((R_GIC*EstimationEconomy.agents[(int(Params.pref_type_count)-1)].DiscFac)**(1/Params.CRRA))*Params.LivPrb_i[0])/(Perm_Gro_em*Ex_psi_inv)
    GIC_v.append(GIC)
    if (k==0.02):
        print ('The growth impatience factor of the most patient agent is:' + str(GIC))

GIC_path = Folder_path+'\GIC.png'
plt.ylabel('Growth Impatience Factor')
plt.xlabel('Std Dev of Perm. Income Shock')
plt.scatter(std_GIC,GIC_v)
plt.savefig(GIC_path)
# Exercise conducted for a range of values for PermShkStd
for k in np.arange(0.005,0.021,0.001):   
    print('**************************')
    print k
    ShockStd = [(k*4/11)**0.5]   # standard deviation for permanent shock 
    #BaselineType.PermShkStd = [(0.05*4/11)**0.5]
    BaselineType.TranShkStd =[(0.01*4)**0.5]
    BaselineType.PermShkStd =ShockStd    
    for j in range(len(EstimationAgentList)):
        cstwMPC.cstwMPCagent.updateIncomeProcess(EstimationEconomy.agents[j]) 
    
    #Display statistics about the estimated model
    EstimationEconomy.LorenzBool = True
    EstimationEconomy.ManyStatsBool = True
    EstimationEconomy.distributeParams(Params.param_name,Params.pref_type_count,center_estimate,spread_estimate,Params.dist_type)
    EstimationEconomy.center_estimate = center_estimate
    EstimationEconomy.spread_estimate = spread_estimate
    for j in range(len(EstimationAgentList)):
        EstimationEconomy.agents[j].PermShkStd = ShockStd
    for j in range(len(EstimationAgentList)):
        cstwMPC.cstwMPCagent.updateIncomeProcess(EstimationEconomy.agents[j]) 
    
    #print ('Permanent Shock before is: ',EstimationEconomy.agents[1].TranShkStd)
    EstimationEconomy.solve()
    EstimationEconomy.calcLorenzDistance()
    #print ('Permanent Shock after is: ',EstimationEconomy.agents[1].PermShkStd)
    #print('***************************')
    #print('Estimate is center=' + str(center_estimate) + ', spread=' + str(spread_estimate) + ', took ' + str(t_end-t_start) + ' seconds.')
    EstimationEconomy.showManyStats(Params.spec_name)
    
    # Calculate and print variables of interest
    C=np.sum(np.hstack(EstimationEconomy.pLvlNow)*np.hstack(EstimationEconomy.cNrmNow)) # Aggregate Consumption Level
    A=np.sum(np.hstack(EstimationEconomy.pLvlNow)*np.hstack(EstimationEconomy.aNrmNow)) # Aggregate Assets
    M=np.sum(np.hstack(EstimationEconomy.pLvlNow)*np.hstack(EstimationEconomy.mNrmNow)) # Aggregate Market Resources
    Y=np.sum(np.hstack(EstimationEconomy.pLvlNow)*np.hstack(EstimationEconomy.TranShkNow)) # Aggregate Labor Income
    B=M-Y 
    I=(BaselineType.Rfree-1)*B+Y # Aggregate Income
    SR=(I-C)/I # Aggregate Saving Rate
    MPSall=1-EstimationEconomy.MPCall # MPS
    AY=A/Y # Asset to Income Ratio
    print('A =',A)
    print('M =',M)
    print('Y =',Y)
    print 'C =',C
    print 'SR =',SR
    print 'AY =',AY
    #print(EstimationEconomy.AaggNow)
    #print(EstimationEconomy.AFunc)
    #print(np.sum(np.hstack(EstimationEconomy.aLvlNow)))

    # Construct an array for MPS and ASR to plot
    MPS.append(MPSall)
    ASR.append(SR)
    AtoY.append(AY)

#Plot the relationship between MPS/ASR and Std Dev of Perm Shk
std=(np.arange(0.005,0.021,0.001)*4/11)**0.5

Result_data_path = Folder_path+'\SavingVSPermShr_Youth_MPC_15.png'
plt.ylabel('Aggregate Saving Rate')
plt.xlabel('Std Dev of Perm. Income Shock')
#plt.title('Change in Savings Following Increase in Permanent Income Uncertainty')
plt.ylim(0.08,0.16)
plt.scatter(std,ASR)
# Draw the linear fitted line
m, b = np.polyfit(std, ASR, 1)
plt.plot(std, m*std + b, '-')
plt.savefig(Result_data_path)
slope, intercept, r_value, p_value, std_err = sp.stats.linregress(std,ASR)
print('Slope=' + str(slope) + ', intercept=' + str(intercept) + ', r_value=' + str(r_value) + ', p_value=' + str(p_value)+', std=' + str(std_err))
