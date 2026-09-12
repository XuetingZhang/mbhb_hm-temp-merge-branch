# %%
import numpy as np
import matplotlib.pyplot as plt

from TDIPhemonHM import TDIPhenomHM_AET
from PSD import TianQinNoise
from Likelihood import SampPara, WhittleLikelihood, HeterodynedLikelihood




#
from schwimmbad import MPIPool

import sys
sys.path.append("../utils/")
sys.path.append("../signal_simulation/")

# import prior_prep as data_prep



import matplotlib.pyplot as plt
import os

from astropy.cosmology import Planck15 as cosmo

# Training hyperparameter setting
from tqdm.auto import tqdm

from eryn.ensemble import EnsembleSampler
from eryn.state import State
from eryn.prior import ProbDistContainer, uniform_dist
from eryn.utils import TransformContainer
from eryn.moves import GaussianMove, StretchMove, CombineMove
from eryn.utils.utility import groups_from_inds
from eryn.moves import MHMove
from eryn.backends import HDFBackend
import eryn.backends as ebackends

from skymovetest import SkyMove

import multiprocessing as mp
# Set random seed
np.random.seed(42)
import corner
# import likelihood as like
from scipy.signal import correlate

from chainconsumer import Chain, ChainConfig, ChainConsumer, make_sample, Truth
import pandas as pd
import gc




case=17
Tobs = 5*86400

redshift = 6.791268942303133
redshift2 = cosmo.luminosity_distance(2).value/1000 # 15.924566651659156
delta_tc= 15*60 #int(0.4*3600)  #15*60
tc = Tobs +delta_tc


# The injection 
# par_array: 
# [0] Mc, [1] eta, [2] chi1z, [3] chi2z, 
# [4] distance, [5] tc, [6] phic, 
# [7] lambda, [8] beta, [9] psi, [10] iota

case = 27
par_array = np.asarray([1e6, 0.2, 0.3, 0.4,
                        redshift2, tc, np.pi/2,
                        np.pi, np.pi/3, np.pi/3, np.pi/6])
case = 271
par_array = np.asarray([9e5, 0.2, 0, 0,
                        redshift2, tc, np.pi/2,
                        np.pi, np.pi/3, np.pi/3, np.pi/6])

case = 272
par_array = np.asarray([9e5, 0.2, 0, 0,
                        redshift2, tc, np.pi/2,
                        np.pi/3., np.pi/3, np.pi/3, np.pi/6])

# # case =17
# par_array = np.asarray([3e5, 0.2, 0, 0,
#                         redshift2, tc, np.pi/2,
#                         np.pi, np.pi/3, np.pi/4, np.pi/3])

# case = 37
# par_array = np.asarray([3e5, 0.2, 0, 0,
#                         redshift2, tc, np.pi/3,
#                         np.pi, np.pi/3, np.pi/4, np.pi/3])
# # par_array = np.asarray([7e5, 0.2, 0.0, 0.0,
# #                         redshift2, tc, np.pi/2,
# #                         np.pi, np.pi/3, np.pi/3, np.pi/6])

# case =171
# par_array = np.asarray([3e5, 0.2, 0, 0,
#                         redshift2, tc, np.pi/3,
#                         np.pi/3., np.pi/3, np.pi/4, np.pi/3])

# case =172
# par_array = np.asarray([5e5, 0.2, 0, 0,
#                         redshift2, tc, np.pi/3,
#                         np.pi/3., np.pi/3, np.pi/3, np.pi/3])

# case = 273
# par_array = np.asarray([9e5, 0.2, 0, 0,
#                         redshift2, tc, np.pi,
#                         np.pi/3., np.pi, np.pi/3, np.pi/6])

case = 274
par_array = np.asarray([9e5, 0.2, 0, 0,
                        redshift2, tc, np.pi,
                        np.pi/3., np.pi, np.pi/5, np.pi/6])

case = 275
par_array = np.asarray([9e5, 0.2, 0, 0,
                        redshift2, tc, np.pi,
                        np.pi/3., 6, np.pi/2, np.pi/6])

samp_par_array = SampPara(par_array)


# %%
fs = 0.01
# dt = 5
dt = 1./fs
times = np.arange(0,Tobs,dt)
freq_output = np.fft.rfftfreq(len(times),dt)

# %%
# orbit setting at t=0, all default to zero
kappa0=0       # angle between the first spacecraft and x axis
kappa_earth=0  # ecliptic longitude of the geocenter
beta0=0        # ecliptic longitude of the perihelion
eccTianqin=0   # eccentricity of TianQin

# %%
# %time 
frequency, Achannel, Echannel, Tchannel = TDIPhenomHM_AET(par_array, Tobs, freqs_output=freq_output, run_phenomd=False, kappa0=kappa0, kappa_earth=kappa_earth, beta0=beta0, eccTianqin=eccTianqin)

print('Npoint:',len(frequency[np.where(Achannel!=0)]))

# %%
plt.loglog(frequency, abs(Achannel), label='A')
plt.loglog(frequency, abs(Echannel), label='E')
plt.loglog(frequency, abs(Tchannel), label='T')
plt.legend()
plt.xlim(2e-4,5e-4)

# %%
SAE, ST = TianQinNoise().noise_AET(frequency)

data = np.array([Achannel, Echannel, Tchannel])
Snf = np.array([SAE, SAE, ST])

# %%
Whittlell = WhittleLikelihood(Tobs, frequency, data, Snf, run_phenomd=False, kappa0=kappa0, kappa_earth=kappa_earth, beta0=beta0, eccTianqin=eccTianqin)
# %time 
Whittlell.lnlike(samp_par_array)


# %%
from Likelihood import AET_Innprod_wave
idx = (Achannel!=0)
delta_f = np.gradient(frequency[idx])
dd_inn=-AET_Innprod_wave(Achannel[idx], Echannel[idx], Tchannel[idx], SAE[idx], ST[idx], delta_f)
print(f"-0.5* <d|d> \n:{-0.5*dd_inn}")
print(f" SNR:{np.sqrt(-1*dd_inn)}")

# %%
# tc_list = np.linspace(5.4*86400,5.6*86400,1000)
# Ntc = len(tc_list)
# ll_list = np.zeros(Ntc)
# for i in range(Ntc):
#     samp_par = np.copy(samp_par_array)
#     samp_par[5] = tc_list[i]
#     ll_list[i] = Whittlell.lnlike(samp_par)

# %%
index = 6
lam_list = np.linspace(0,2*np.pi,500)
priors = lam_list.copy()
samp_par_array = SampPara(par_array)
Nlen = len(priors)
# inject_theta = samp_par_array[index]
ll_lam_list=np.zeros(len(lam_list))
for i in range(Nlen):
    samp_par2 = samp_par_array.copy()
    samp_par2[index] = lam_list[i]
    ll_lam_list[i] = Whittlell.lnlike(samp_par2)

# %%
plt.figure()
plt.plot(priors,ll_lam_list)
plt.axvline(samp_par_array[index],color='r',ls=':')
plt.axhline(np.max(ll_lam_list),color='r',ls='--')
plt.savefig('../../PTMCMC_Eryn/'+'case_'+str(case)+'-theta_'+str(index)+'.png')

# %%
# plt.plot(tc_list,ll_list)
# plt.axvline(5.5*86400,color='r')

# %%
# Heterodynedll = HeterodynedLikelihood(samp_par_array, Tobs, frequency, data, Snf, run_phenomd=False, kappa0=kappa0, kappa_earth=kappa_earth, beta0=beta0, eccTianqin=eccTianqin)
# # %time 
# Heterodynedll.lnHetLike(samp_par_array)

# %%
# para                   lnMc,  eta, chi1, chi2,  Dis,     tc, phic, lambda, sin_beta,  psi, cos_iota

tc_max = Tobs + 86400*2
min_p = np.array([np.log10(1e5), 0.05,   -1,   -1, 0.01,      0,    0,      0,       -1,    0,      -1])
max_p = np.array([np.log10(1e7), 0.25,    1,    1, 230., tc_max, 2*np.pi,   2*np.pi,        1,   np.pi,       1])


# %%
# Whittlell = WhittleLikelihood(Tobs, freq, data, Snf, kappa0, kappa_earth)
freq = freq_output.copy()
truth_samp_para = samp_par_array.copy()
Heterodynedll = HeterodynedLikelihood(truth_samp_para, Tobs, freq, data, Snf, False, kappa0, kappa_earth)

############# lnprob defines #############
def lnprob(x):
    if (max_p[0]>=x[0]>=min_p[0] and 
        max_p[1]>=x[1]>=min_p[1] and 
        max_p[2]>=x[2]>=min_p[2] and 
        max_p[3]>=x[3]>=min_p[3] and 
        max_p[4]>=x[4]>=min_p[4] and 
        max_p[5]>=x[5]>=min_p[5] and 
        max_p[6]>=x[6]>=min_p[6] and 
        max_p[7]>=x[7]>=min_p[7] and 
        max_p[8]>=x[8]>=min_p[8] and 
        max_p[9]>=x[9]>=min_p[9] and 
        max_p[10]>=x[10]>=min_p[10]):
        
        logp = 2*np.log(x[4])
        # logL = Whittlell.lnlike(x)
        logL = Heterodynedll.lnHetLike(x)
        
        # Avoid getting stuck in a prior heights.
        if (logp > logL):
            return logL
        else:
            return logL+logp
    else:
        # return -np.inf
        return -1e300




# %%
x = truth_samp_para.copy()
log = lnprob(x)
print(log)


# %%
# 2-d test
# Parameter lists and indices
# mbhb_params =[0,7,8,1,5,4,  9, 10, 6]
# params_list =[0,7,8,6,1,2,  9, 3,10] #

# mbhb_params =[0,7,8]
# params_list =[0,7,8] #
mbhb_params =[0,7,8,1,5,4,2,3]
params_list =[0,7,8,6,1,2,21,22] # for name list index

mbhb_params =[0,7,8,1,5,4,   10,9, 6]
params_list =[0,7,8,6,1,2,   3,9,10] # for name list index


legend_list =['chirp mass','merger time','luminosity distance','inclination','spin1z','spin2z','symmetric mass ratio','longitude','lantitude','polarization','merger phase','initial frequency','rho','SNR','m1','m2','chi_eff','eccentricity','cos_lam','chi_a','chi_b']
signs_list =[r'$ \log \mathcal{M}_c [M_{\odot}]$ ', r'$\Delta t_c [sec]$ ','dist [Gpc]',r'$\cos \iota$', r'$\chi_{1z}$',r'$\chi_{2z}$',r'$\eta$',r'$\lambda$',r'$\sin \beta$',r'$\psi$',r'$\phi_c$',r'$f_0$',r'\rho',r'SNR',r'$m_1$',r'$m_2$',r'$\chi_{\rm eff}$',r'$e_0$',r'q',r'$\cos \lambda$',r'$\cos \beta$',r'$\chi_a$',r'$\chi_b$']
params_names =['logmc','tc','dist','cosiota','chi1z','chi2z','eta','longitude','sinlatitude','psi','phic','f0','rho','Rho','m1','m2','chi','e0','q','coslongitude','coslatitude','chi_a','chi_b'] #legend_list[:3]
labels =[]
parameter_names =[]
new_params = params_list[:]
extra=0
if 7 in params_list and extra ==1:
    new_params.append(19)
N = len(new_params)
Ndim = len(new_params)
for i,j in enumerate(new_params):
    print(i,j)
    if j==7 and extra ==1:
        label_name = r'$\sin$'+ signs_list[j]
        paras_name = "sin" +params_names[j]
    
    if j==3:
        label_name = r"$\iota$"
        paras_name = "iota"

    else:
        label_name = signs_list[j]
        paras_name = params_names[j]
    labels.append(label_name)
    parameter_names.append(paras_name)# legend_list[:3]
        
    print(f"paramters name:{parameter_names}")



# %%
def wrap_func(y, truths=[], mbhb_params=[]):
    
    # y is the samples from the priors, assume the parameters defined by mbhh_params array
    # mbhb_params is the array defines the which array of the parameters we are looking for


    if len(mbhb_params) == 0 and len(y) == 11:

        return lnprob(y)
    elif len(y) <11 and len(mbhb_params) <=11:

        temp = truths.copy()

        for i,j in enumerate(mbhb_params):
            temp[j]  = y[i]
        

        return lnprob(temp) 


# test_para =[truth_samp_para[0],truth_samp_para[7], 0] # lam,beta
# test_para2 =[truth_samp_para[0],truth_samp_para[7],truth_samp_para[8] ]

test_para2 = np.zeros(Ndim)
for i,j in enumerate(mbhb_params):
    test_para2[i] = truth_samp_para[j]

# logp1 = wrap_func(test_para,truths=truth_samp_para,mbhb_params=mbhb_params)
logp2 = wrap_func(test_para2,truths=truth_samp_para,mbhb_params=mbhb_params)

# print(logp1)
# print(logp2)

# %%
test_list = np.linspace(0, 2*np.pi,500)
log_list =np.zeros(len(test_list))

# for k,j in enumerate(test_list):
#     test_para3= [j, truth_samp_para[8]]
#     log_list[k] = wrap_func(test_para3,truths=truth_samp_para,mbhb_params=mbhb_params)




# %%
# index=7
# plt.figure()
# plt.plot(test_list,log_list,'b')
# plt.axvline(truth_samp_para[index],color='r',ls=':')
# plt.axhline(np.max(log_list),color='r',ls='--')
# plt.show()

# %%



z_prior=2.5
z_min=0.1
Mc_max=5#truth_samp_para[0] +1
Mc_min=6#truth_samp_para[0] -0.5
tc_prior=int(20*60)
tc_min=int(10*60)
# tc_prior=int(0.5*3600)
# tc_min=int(0.3*3600)



tc_prior=600
tc_min=1200
# breakpoint()





#  Setting the sampler
# Sampling setup
nsteps = 200000
ntemps = 10
burn = 10#00
thin_by = 1
nwalkers = 80
ncores = 56
ndims = {"mbh": len(mbhb_params)}
nleaves_max = 1 # 1
nleaves_min = 1 # 1
branch_names = ["mbh"]
trace=50000
# SkyMove preserves the target distribution and only changes sky-mode exploration.
move_frac=0.20
Ndim= len(mbhb_params)


injection_params_sub=[np.zeros(Ndim) ]
injection_params2 = np.zeros(len(mbhb_params))
for i, j in enumerate(mbhb_params):
    injection_params2[i] = truth_samp_para[j]
    injection_params_sub[0][i] = truth_samp_para[j]




ll_ref = logp2
ll0 =ll_ref

# start postion
# injection_params = par_array.copy()
# injection_params_sub = []
# chi1 = injection_params[2]
# chi2 = injection_params[3]
# for i in mbhb_params:
#     item = injection_params[i]
#     print(f"item:{item}-redshfit item:{injection_params[i]}")
#     if i == 8:
#         item =np.sin(item)
#     # elif i ==10:
#     #     item =np.cos(item)
#     # elif i == 5:
#     #     item = item - Tobs
#     elif i ==0:
#         item = np.log(item)
    
#     # elif i ==10:
#     #     # inclination : (0,np.pi)
#     #     item = np.cos(item)

#     elif i == 2:
        
#         item = 0.5*(chi1 +chi2)
#     elif i == 3:
#         # chi_minus
#         item = 0.5*(chi1 - chi2)

#     injection_params_sub.append(item)
# injection_params_sub =[np.array(injection_params_sub)] # a branch of the true injections: like assuming guassin model with 2 guassian signals
print(f"injection_params_sub:{injection_params_sub}")

print(f"\n")






# coords
# start 2 : start with true value
# if cos(iota)=1, 1+1e-5 >1 error
coords = {'mbh': np.where(
    injection_params_sub[0] != 0,
    injection_params_sub[0][None, None, None, :] * (1 + 1e-3 * np.random.randn(ntemps, nwalkers, nleaves_max, Ndim)),
    1e-4 * np.random.randn(ntemps, nwalkers, nleaves_max, Ndim))}
print(f"coords shape:{coords['mbh'].shape}")












out ='./test_temp/'

delta_tc=truth_samp_para[5]
Mc= truth_samp_para[0]
Ndays = int(Tobs/86400)
data_dir='/public_new/work_space/zhangxt57/mbhb_data/mbhbhm_ptmcmc/'
trace_dir='/public_new/work_space/zhangxt57/Project_PostDoc/mbhb_hm/signal_simulation_hm/PhenomHM/test_temp/'
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

up_fn=1
init=7
flg='Smallrange-' # full dimentional test
flg='Wittlikelihood-'
flg='Heterodyned-'
sub_dir=flg+str(Ndim)+'-dim-case-'+str(case)+'_deltaTc_'+str(delta_tc)+'_Mc_'+str(int(Mc))+'_movefrac_'+str(move_frac)+'_Tobs_'+str(Ndays)+'days'+'-fs-'+str(fs)+'-steps'+str(nsteps)+'-nwalkers-'+str(nwalkers)+'-updatefn-'+str(up_fn)+'/'
# '-redshift'+str(z)+'-tc-prior-'+str(tc_min)+'-'+str(tc_prior)+'-redshift-max'+str(z_prior)+'-z_min-'+str(z_min)+'-init-para-'+str(init)+'-thin-by-'+str(thin_by)+'-fullband-'+str(int(fullband))+'-tracestep-'+str(trace)+'/'
out=os.path.join(data_dir,sub_dir)
if not os.path.exists(out):
    os.makedirs(out)
print(f"output path:{out}")




#---------------

#---------------------
# update figures during running
# Step 2: Calculate Autocorrelation Time
def calculate_autocorrelation_time(samples, max_lag=100):
    npoints, ndim = samples.shape
    autocorr_time = np.zeros(ndim)
    
    for dim in range(ndim):
        chain = samples[:, dim].flatten()
        mean = np.mean(chain)
        var = np.var(chain, ddof=1)
        
        if var < 1e-10:
            # Prevent division by zero
            autocorr_time[dim] = max_lag
            continue
        
        x = chain - mean
        result = correlate(x, x, mode='full')
        auto_corr = result[result.size // 2:] / result[result.size // 2]
        auto_corr /= var
        
        tau = 1
        for i in range(1, max_lag):
            if auto_corr[i] < 0:
                break
            tau += 2 * auto_corr[i]
        
        autocorr_time[dim] = tau
    
    return autocorr_time




# Step 3: Calculate Effective Sample Size (ESS)
def calculate_ess(nsteps, autocorr_time):
    ess = nsteps / autocorr_time
    return ess



def next_pow_two(n):
    i = 1
    while i < n:
        i = i << 1
    return i


def autocorr_func_1d(x, norm=True):
    x = np.atleast_1d(x)
    if len(x.shape) != 1:
        raise ValueError("invalid dimensions for 1D autocorrelation function")
    n = next_pow_two(len(x))

    # Compute the FFT and then (from that) the auto-correlation function
    f = np.fft.fft(x - np.mean(x), n=2 * n)
    acf = np.fft.ifft(f * np.conjugate(f))[: len(x)].real
    acf /= 4 * n

    # Optionally normalize
    if norm:
        acf /= acf[0]

    return acf
# Automated windowing procedure following Sokal (1989)
def auto_window(taus, c):
    m = np.arange(len(taus)) < c * taus
    if np.any(m):
        return np.argmin(m)
    return len(taus) - 1


# Following the suggestion from Goodman & Weare (2010)
def autocorr_gw2010(y, c=5.0):
    f = autocorr_func_1d(np.mean(y, axis=0))
    taus = 2.0 * np.cumsum(f) - 1.0
    window = auto_window(taus, c)
    return taus[window]


def autocorr_new(y, c=5.0):
    f = np.zeros(y.shape[1])
    for yy in y:
        f += autocorr_func_1d(yy)
    f /= len(y)
    taus = 2.0 * np.cumsum(f) - 1.0
    window = auto_window(taus, c)
    return taus[window]


def update_fig(iteration,state,sampler,outdir='./T'+flg+'-'+str(case)+'_Mc_'+str(int(Mc))+'_movefrac_'+str(move_frac)+'_deltaTc_'+str(delta_tc)+'-tracestep-'+str(trace)+'-ndim'+str(Ndim)+'-fs-'+str(fs)+'-nsteps-'+str(nsteps)+'-nwalker-'+str(nwalkers)+'_Tobs_'+str(Ndays)+'days-Mmin-'+str(Mc_min)+'-Mmax-'+str(Mc_max)+'-init-'+str(init)+'-tc-prior-'+str(tc_min)+'-'+str(tc_prior)+'-redshift-max'+str(z_prior)+'-thin-by-'+str(thin_by)+'/'):
    """
    input: sampler and truth ,saving dir
    """
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    print(f"iteration---{iteration}")
   
    if iteration > burn and iteration +1 != nsteps  :
        # breakpoint()
        fig, ax = plt.subplots(ndims['mbh'], 1)
        fig.set_size_inches(20, 18)

        samps = sampler.get_chain()['mbh']
        #
        # plotwalkers= int(nwalkers/4) # 
        plotwalkers= nwalkers
        thinby=10
        for i in range(ndims['mbh']):
            for walk in range(plotwalkers):
                ax[i].plot(samps[:, 0, walk, :, i][::thinby],'o',alpha=0.9,markersize=2)
                ax[i].axhline(y=injection_params_sub[0][i],xmin=0,xmax=iteration,color='r')
                ax[i].set_ylabel(labels[i])
                ax[i].set_xlabel('steps')
        # plt.legend(loc)
        plt.savefig(outdir+"/chians-individual-"+str(iteration)+".png")
        plt.close()
        # breakpoint()
        
        samples = sampler.get_chain()["mbh"][:, 0].reshape(-1, Ndim)
        # # samples2 =chain = het_sampler.get_chain()["mbh"][:, 0, :, 0].reshape(-1, Ndim)
  

        cutoff = int(0.5*samples.shape[0])
        samples = samples[~np.isnan(samples[:,0])][cutoff:,:]
        samples = samples[np.isfinite(samples[:,0])][:]
        
        corner_kwargs = dict(
                bins=32,
                smooth=0.9,
                color="teal",
                # quantiles=[0.16, 0.84, 0.95],
                levels=(1 - np.exp(-0.5), 1 - np.exp(-2), 1 - np.exp(-9 / 2.0)),
                # levels=(0.39346934,0.86466472,0.988891),
                plot_density=True,
                plot_datapoints=True,
                fill_contours=True,
                show_titles=True,
                title_fmt='.4f',
                hist_kwargs=dict(density=True),
                )
        # ranges = [(np.min(samples[:,i]), np.max(samples[:,i])) for i in range(Ndim)]
        ranges = [
            (min(np.min(samples[:,i]), injection_params_sub[0][i]), max(np.max(samples[:,i]), injection_params_sub[0][i])) 
            if samples[:,i].size 
            else (-1,1) 
            for i in range(Ndim)
        ]

        try:
            fig = corner.corner(samples,truths=injection_params_sub[0],labels=labels,range=ranges,**corner_kwargs)
            ax = fig.axes
            # for mean in means:
            #     ax[4].axvline(mean)
            # Overplot lines marking "true" values
            corner.overplot_lines(fig, injection_params_sub[0], color='r')
            plt.savefig(outdir+"/corner-"+str(iteration)+".png")
            plt.close()

        except:
            pass
 


        ll = sampler.backend.get_log_like()
       
        # Notice the shape of the Likelihood is (nsteps, ntemps, nwalkers) (in this example we have 1 temperature). 
        
        nT=2
        fig, ax = plt.subplots(nT, 1) # according to the number of tempratures
        fig.set_size_inches(20, 20)
        # for i in range(ndims['mbh']):
        ax[0].set_title('Log likelihood',fontsize=20)
        ax[0].axhline(y=ll_ref,xmin=0,xmax=iteration,color='k')
        ax[0].axhline(y=ll0,xmin=0,xmax=iteration,color='r')
        for i in range(nT):
            for walk in range(nwalkers):
                ax[i].plot(ll[:,i,walk].reshape(-1),'o',alpha=0.7)
                
                
                ax[i].set_ylabel('$T_{%d}$'%(int(i)))
                ax[i].set_xlabel('steps')
        
        plt.tight_layout()        
        plt.savefig(outdir+"/log-likelihood-individual-"+str(iteration)+".png")
        plt.close()

        print(f"acceptance rate:{sampler.acceptance_fraction.shape}")
        # #  tracing the acceptance rate
        # plt.figure()
        # plt.plot(range(nwalkers),sampler.acceptance_fraction[0])
        # plt.ylabel('acceptance rate',fontsize=16)
        # plt.xlabel('walkers at 0 temperature',fontsize=16)
        # plt.savefig(outdir+'/acceptance_rate_fig_'+str(iteration)+'.png')
        # plt.close()


    return 0


#-----------------







# Setting up the backend
# diskpth='/data2/zhangxt57/mbhb_data/fim_and_ptemper2/'
diskpth= data_dir
# resumepth=diskpth+'/11-dim-case-621-steps200000-nwalkers-80-updatefn-1-redshift1/'
# resume =False
# if resume:
#     backendname1 =resumepth+"/test.h5"
#     backendame1 = out+"/output.h5" 
# else:
#     print("---not resuming")
#     backendame1 = "output.h5"
# backendname =out+"/output.h5"
# backend = HDFBackend(backendname)



perid_index = mbhb_params.index(7)
# dL_max = 47.73160011083495 # z=5
# dL_min = 0.08  # z=0.02
dL_max = cosmo.luminosity_distance(z_min).value/1000
dL_min = cosmo.luminosity_distance(z_prior).value/1000 #0.08  # z=0.02

priors = {"mbh": ProbDistContainer({
    mbhb_params.index(0):  uniform_dist(Mc_min,Mc_max),
    perid_index: uniform_dist(0,np.pi*2), # logitude
    mbhb_params.index(8): uniform_dist(-1,1),  # latitude:[-1,1]->arcsin :[-pi/2,pi/2]
    mbhb_params.index(1): uniform_dist(0.05,0.25),
    mbhb_params.index(5): uniform_dist(tc_min,tc_prior),
    mbhb_params.index(4): uniform_dist(dL_min,dL_max),# dist
    # mbhb_params.index(2): uniform_dist(-0.99,0.99), # chi1
    # mbhb_params.index(3): uniform_dist(-0.99,0.99), # chi2
    mbhb_params.index(10): uniform_dist(-1,1) ,# cos(iota) ->arcos : [0,pi] 
    mbhb_params.index(9): uniform_dist(0,np.pi),# psi : 0,pi
    mbhb_params.index(6): uniform_dist(0,np.pi*2)# phic  
})}


sinlat_index = mbhb_params.index(8)
periodic = {"mbh": {perid_index: 2 * np.pi}}#, 2:0.5* np.pi}}
# The sampler state uses (longitude, sin(latitude)), so the sky move has
# zero proposal Jacobian and does not change the intended posterior target.
sky_move = SkyMove(
    ind_map={"lon": perid_index, "sinlat": sinlat_index},
    sky_representation="lon_sinlat",
    which="both",
    include_identity=False,
    branches=["mbh"],
)
moves = [
    (sky_move, move_frac),
    (StretchMove(), 1.0 - move_frac),
]

ncpu =  mp.cpu_count()
print("{0} CPUs".format(ncpu))
ncores = ncpu
betas = np.linspace(1.0, 0.0, ntemps)
print(f"betas for temperature:{betas}")

# Sampling

backendname =out+"/output.h5"
backend = HDFBackend(backendname)
# het_sampler.backend.reset(*het_sampler.backend.reset_args,**het_sampler.backend.reset_kwargs)

with mp.Pool(ncores) as pool:
    sampler = EnsembleSampler(
        nwalkers,
        ndims,
        # likelihood_heter.lnHetLike,
        wrap_func,
        priors,
        args=(truth_samp_para, mbhb_params),
        # args=(fixed_parameters, freqs, analysis),
        update_fn = update_fig,
        update_iterations = trace,
        nbranches=len(branch_names),
        tempering_kwargs=dict(ntemps=ntemps,betas=betas),
        branch_names=branch_names,
        nleaves_max=nleaves_max,
        nleaves_min=nleaves_min,
        periodic=periodic,
        moves=moves, # None
        backend=backend,
        # rj_moves=False,# put False basic generation of new leaves from the prior
        pool=pool
    )

    # het_start_state = State({"mbh": start_params})
    # setup starting state
    # het_start_state  = State(coords, log_like=log_like, log_prior=log_prior, betas=betas, inds=inds)
    het_start_state  = State(coords)
    # breakpoint()

    

  
    
    sampler.run_mcmc(het_start_state, nsteps, burn=burn, progress=True, thin_by=thin_by)
    


mp.Pool().close()



# Post-processing
samples = sampler.get_chain()["mbh"].reshape(-1, len(mbhb_params))
np.save(out+"/samples.npy", samples)

# Corner plot
# labels = [r'$ \log \mathcal{M}_c [M_{\odot}]$', r'$\Delta t_c [sec]$', 'dist [Gpc]', r'$\cos \iota$', r'$\chi_{1z}$', r'$\chi_{2z}$', r'$\eta$', r'$\lambda$', r'$\sin \beta$', r'$\psi$', r'$\phi_c$']
corner.corner(samples, labels=labels, truths=injection_params_sub[0])
plt.savefig(out+"/corner-corner.png")

fig, ax = plt.subplots(Ndim, 1)
fig.set_size_inches(10, 8)
for i in range(Ndim):
    for walk in range(nwalkers):
        # ax[i].plot(,alpha=0.9,linestyle=':')
        points = sampler.get_chain()['mbh'][:, 0, walk, :, i]
        # xmax = len(points)
        ax[i].plot(range(len(points)),points,'o',alpha=0.9)
        ax[i].axhline(y=injection_params_sub[0][i],xmin=0,xmax=nsteps,color='r')
        ax[i].set_ylabel(labels[i])
        ax[i].set_xlabel('steps')
# plt.legend(loc)
plt.savefig(out+"/chians-individual-0.png")
plt.close()

nT=2
iteration=nsteps
ll = sampler.backend.get_log_like()
fig, ax = plt.subplots(nT, 1) # according to the number of tempratures
fig.set_size_inches(20, 20)
# for i in range(ndims['mbh']):
ax[0].set_title('Log likelihood',fontsize=20)
ax[0].axhline(y=0,xmin=0,xmax=iteration,color='blue',ls='--')
# ax[0].axhline(y=ll_ref+dd_inn,xmin=0,xmax=iteration,color='k')
ax[0].axhline(y=ll0+dd_inn,xmin=0,xmax=iteration,color='r')
for i in range(nT):
    for walk in range(nwalkers):
        ax[i].plot(ll[:,i,walk].reshape(-1)+dd_inn,'o',alpha=0.7)
        
        
        ax[i].set_ylabel('$T_{%d}$'%(int(i)))
        ax[i].set_xlabel('steps')

plt.tight_layout()        
plt.savefig(out+"/log-likelihood-individual-"+str(iteration)+".png")
# plt.savefig("log-likelihood-individual-"+str(iteration)+".png")
plt.close()



# chain plot



# %%
# "t_ref": injection_params_sub[3]

fig, ax = plt.subplots(ndims['mbh'], 1)
fig.set_size_inches(10, 8)
for i in range(ndims['mbh']):
    for walk in range(nwalkers):
        # ax[i].plot(,alpha=0.9,linestyle=':')
        points = sampler.get_chain()['mbh'][:, 0, walk, :, i]
        # xmax = len(points)
        ax[i].plot(range(len(points)),points,'o',alpha=0.9)
        ax[i].axhline(y=injection_params_sub[0][i],xmin=0,xmax=nsteps,color='r')
        ax[i].set_ylabel(labels[i])
        ax[i].set_xlabel('steps')
# plt.legend(loc)
plt.savefig(out+"/chians-individual-0.png")
plt.close()



# getting the chain
samples_chains = sampler.get_chain()['mbh']#[:, 0, :,:,:]
print(f"chains.shape:{samples_chains.shape}")

# same as
# samples = enseble.backend.get_chain()
# print(type(samples), samples.keys(), samples["mbh"].shape)
np.save(out+'/chains.npy',samples_chains)

samples_ch = np.load(out+'/chains.npy')

fig, ax = plt.subplots(ndims['mbh'], 1)
fig.set_size_inches(16, 12)
for i in range(ndims['mbh']):
    for walk in range(nwalkers):
        # ax[i].plot(het_sampler.get_chain()['mbh'][:, 0, walk, :, i],linestyle=':',talpha=0.9)
        # ax[i].plot(het_sampler.get_chain()['mbh'][:, 0, walk, :, i],linestyle=':',talpha=0.9)
        ax[i].plot(range(len(samples_chains)),samples_ch[:, 0, walk, :, i], 'o', alpha=0.8)
        ax[i].axhline(y=injection_params_sub[0][i],xmin=0,xmax=nsteps,color='r')
        ax[i].set_ylabel(labels[i])
        ax[i].set_xlabel('steps')

# plt.legend()
plt.savefig(out+"/chians-individual-npydata.png")
plt.close()

# breakpoint()

cutoff = int(0.5*nsteps)
print(f"cutoff:{cutoff} - nsteps mins cutoff:{nsteps-cutoff}")
samples = sampler.get_chain()["mbh"][cutoff:, 0].reshape(-1, Ndim)
print(f"samples shape:{samples.shape}")

samples = samples[~np.isnan(samples[:, 0])][:]
samples = samples[np.isfinite(samples[:,0])][:]

means = np.asarray(injection_params_sub)[:, 1]
corner_kwargs = dict(
        bins=32,
        smooth=0.9,
        color="teal",
        # quantiles=[0.16, 0.84, 0.95],
        levels=(1 - np.exp(-0.5), 1 - np.exp(-2), 1 - np.exp(-9 / 2.0)),
        # levels=(0.39346934,0.86466472,0.988891),
        plot_density=True,
        plot_datapoints=True,
        fill_contours=True,
        show_titles=True,
        title_fmt='.4f',
        hist_kwargs=dict(density=True),
        )
ranges = [(np.min(samples[:,i]), np.max(samples[:,i])) for i in range(Ndim)]
fig = corner.corner(samples,truths=injection_params_sub[0],labels=labels,range=ranges,**corner_kwargs)
ax = fig.axes
# for mean in means:
#     ax[4].axvline(mean)
# Overplot lines marking "true" values
corner.overplot_lines(fig, injection_params_sub[0], color='r')
plt.savefig(out+"/corner.png",dpi=200)
# plt.savefig("./test_temp/corner.png",dpi=200)
# plt.savefig(out+"/corner.pdf",dpi=200)
# breakpoint()


# # calculate auto correction and acceptance rate
# max_lag = 100  # Maximum lag for autocorrelation
# autocorr_time = calculate_autocorrelation_time(samples, max_lag)
# ess = calculate_ess(nsteps * nwalkers, autocorr_time)
# print('Autocorrelation Time:', autocorr_time)
# print('Effective Sample Size (ESS):', ess)
# print('Minimum ESS:', min(ess))


# # Way2 :
# # Compute the estimators for a few different chain lengths
# auto_list =[] #list(np.zeros(Ndim))

# for k in range(Ndim):
#     N = np.exp(np.linspace(np.log(100), np.log(nsteps), 10)).astype(int)
#     gw2010 = np.empty(len(N))
#     new = np.empty(len(N))

#     # 
#     # 
#     # (nsteps, ntemps , nwalkers, nleaves_max , ndims['mbh'])))
#     chain = sampler.get_chain()["mbh"][cutoff: , 0, :, 0, k].T
#     print(f"chain.shape:{chain.shape}")
#     for i, n in enumerate(N):
        
#         gw2010[i] = autocorr_gw2010(chain[:, :n])
#         new[i] = autocorr_new(chain[:, :n])
#         auto_list.append(new[i])
#         i +=1

#     print(f"autocorection:{new[-1]}")
#     print(f"auto_list:{auto_list}")

#     plt.close()
#     plt.figure()
#     # Plot the comparisons
#     plt.loglog(N, gw2010, "o-", label="G&W 2010")
#     plt.loglog(N, new, "o-", label="new")
#     ylim = plt.gca().get_ylim()
#     plt.plot(N, N / 50.0, "--k", label=r"$\tau = N/50$")
#     plt.ylim(ylim)
#     plt.xlabel("number of samples, $N$")
#     plt.ylabel(r"$\tau$ estimates")
#     plt.legend(fontsize=14);
#     plt.savefig(out+'/autocorrection_time_para-'+str(k)+'.png')
#     plt.close()





















# End: plotting figures for checking 

    
df = pd.DataFrame(samples, columns=labels)
h5_path='./'
fn = out+'/Eryn_data_'+str(len(samples))+'.csv'
df.to_csv(fn, index=False)
print("Data has been saved to 'data.csv'.")

del samples
gc.collect()

df =  pd.read_csv(fn)
# df.values[:,4] %= (2 * np.pi)
# df.values[:,5] %= (np.pi)
locations ={}  # dictionary 
# Add varied pairs to the dictionary
for i,value in enumerate(mbhb_params):
    # key = parameter_names[i]
    key = labels[i]
    locations[key] = injection_params_sub[0][i]

# locations[parameter_names[0]] = 10**injection_params_sub[0]
# df.values[:,0] = 10**df.values[:,0]

# df[:,4] %= (2 * np.pi)
# df[:,5]  %= ( np.pi)

print(f"df shape:{len(df)}")
print(f"param name:{parameter_names}")
c = ChainConsumer()
# c.add_chain(Chain(samples=df, name="An Example Contour"))
# df2 = df.values[1000:,:]
chain = Chain(
    samples=df,
    name="Eryn",
    color="b",
    plot_point=True,
    plot_cloud=True,
    marker_style="*",
    marker_size=100,
    num_cloud=30000,
    shade=False,
    linewidth=2.0,
    cmap="magma",
    show_contour_labels=True,
    # color_param="C",
)
c.add_chain(chain)
# You can also override *all* chains at once like so
# Notice that Chain is a child of ChainConfig
# So you could override base properties like line weights... but not samples
c.set_override(ChainConfig(sigmas=[0, 1, 2, 3]))


# c.add_truth(Truth(location={"Mc": injection_params_sub[0], "tc": injection_params_sub[1], "beta": injection_params_sub[2]}))
# c.add_truth(Truth(location={"Mc": injection_params_sub[0], "tc": injection_params_sub[1]}))
c.add_truth(Truth(location=locations))
fig = c.plotter.plot()
plt.savefig(out+'/posteriror-new_likelihood'+str(Ndim)+'-dim.png',dpi=200)
# plt.savefig(out+'/posteriror'+str(Ndim)+'-dim_'+str(new_params)+'.png')
plt.savefig('./test_temp/posteriror'+str(Ndim)+'-dim_'+str(new_params)+'.png')
plt.close()
print(f"Truth:{locations}")





ll = sampler.backend.get_log_like()
lp =sampler.backend.get_log_prior()
print(dir(sampler))
print(f"acceptance rate:{sampler.acceptance_fraction.shape}")
plt.figure()
plt.plot(range(nwalkers),sampler.acceptance_fraction[0])
plt.ylabel('acceptance rate',fontsize=16)
plt.xlabel('walkers at 0 temperature',fontsize=16)
plt.savefig(out+'/acceptance_rate_fig.png')
plt.close()


print(f"swap acceptance rate:{sampler.swap_acceptance_fraction}")
# autocorr_time = het_sampler.get_autocorr_time()

# np.save(out+'/log_like.npy',ll)
# np.save(out+'/log_prior.npy',lp)
print(f"ll.shape:{ll.shape},log_prior:{lp.shape}")


fig, ax = plt.subplots(ntemps, 1) # according to the number of tempratures
fig.set_size_inches(20, 20)
# for i in range(ndims['mbh']):
ax[0].set_title('Log likelihood',fontsize=20)
ax[0].axhline(y=ll0,xmin=0,xmax=nsteps,color='r')
for i in range(ntemps):
    #
    
    for walk in range(nwalkers):
        ax[i].plot(ll[:,i,walk].reshape(-1),'o',alpha=0.7)
        ax[i].set_ylabel('$T_{%d}$'%(int(i)))
        ax[i].set_xlabel('steps')
plt.tight_layout()        
plt.savefig(out+"/log-likelihood-individual.png")
plt.close()


# fig, ax = plt.subplots(ntemps, 1) # according to the number of tempratures
# fig.set_size_inches(20, 20)
# ax[0].set_title('Log prior',fontsize=20)
# for i in range(ntemps):
#     #
#     for walk in range(nwalkers):
#         ax[i].plot(lp[:,i,walk].reshape(-1))
#         ax[i].set_ylabel('$T_{%d}$'%(int(i)))
#         ax[i].set_xlabel('steps')
# plt.tight_layout()
# plt.savefig(out+"/log-prior-indidualtemp.png")
# plt.close()
# # breakpoint()
