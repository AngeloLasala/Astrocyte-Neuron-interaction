"""
Cloosed-loop gliotrasmission .

Extrascelluar neurotrasmitter concentration, averaged over 500 synapses,
with and without gliotrasmission

- "Modelling neuro-glia interactions with the Brian2 simulator" Stimberg et al (2017)
"""
import matplotlib.pyplot as plt
from brian2 import *
from AstrocyteNeuron_Interactions.Brian2_tutorial.connectivity import Connectivity_plot


#####  PARAMETERS  #######################################################
## General Parameters ## 
N_syn = 500                # Total number of synapses
N_a = 1                    # Total number of astrocyte
duration = 20*second       # Total simulation time

## Synapses parameters ##
rho_c = 0.005                 # Synaptic vesicle-to-extracellular space volume ratio (bigger then G_ChI_astrpcyte.py)
Y_T = 500*mmolar              # Total vesicular neurotransmitter concentration
Omega_c = 40/second           # Neurotransmitter clearance rate
U_0__star = 0.6               # Resting synaptic release probability
Omega_d = 2.0/second          # Synaptic depression rate
Omega_f = 3.33/second         # Synaptic facilitation rate
Omega_d = 2.0/second          # Synaptic depression rate
O_G = 1.5/umolar/second       # Agonist binding (activating) rate
Omega_G = 0.5/(60*second)     # Agonist release (deactivating) rate


## Astrocye parameters ##
# -- Calcium - CICR --
Omega_C = 6.0/second       # Maximal rate of Ca^2+ release by IP_3Rs
Omega_L = 0.1/second       # Maximal rate of calcium leak from the ER
O_P = 0.9*umolar/second    # Maxium rate of SERCA uptake
d_1 = 0.13*umolar       # IP_3 binding affinity
d_2 = 1.049*umolar      # Ca inactivation dissociation costant
d_3 = 0.9434*umolar     # IP3 dissociation constant
d_5 = 0.08234*umolar    # Ca activation dissociation costant
C_T = 2.0*umolar        # Total cell free Calcium concentration
rho_A = 0.185           # Ratio between ER volume and cytosol
O_2 = 0.2/umolar/second    # IP3R binding rate for Ca inhibition
K_P = 0.1*umolar        # SERCA calcium affinity

# -- IP3 methabolism --
#degradation
Omega_5P = 0.1/second        # Maximal rate of degradation by IP3-5P
O_3K = 4.5*umolar/second     # Maximal rate of degradation by IP3-3K
K_3K = 1.0*umolar         # IP3 affinity of IP3-3K, muM
K_D = 0.5*umolar          # Ca affinity of IP3-3K, muM

#PLC_delta production 
O_delta = 0.2*umolar/second  # Maximal rate of IP3 production by PLC_delta
kappa_delta = 1.5*umolar  # Inhibition constant of PLC_delta activity
K_delta = 0.3*umolar      # Ca affinity of PLC_delta

#PLC_beta production, agonist(glutammate) dependent
O_beta = 5*umolar/second   # Maximal rate of IP3 production by PLC_beta
K_KC = 0.5*umolar       # Ca affinity of PKC

# -- Gamma_A - fraction of activated astrocyte (Gprotein receptors) --
O_N = 0.3/umolar/second    # Agonist binding rate
Omega_N =0.5/second        # Maximal inactivation rate
zeta = 10                  # Maximal reduction of receptor affinity by PKC

# -- Gliotrasmitter --
C_Theta = 0.5*umolar        # Ca^2+ threshold for exocytosis
Omega_A = 0.6/second        # Gliotransmitter recycling rate
U_A = 0.6                   # Gliotransmitter release probability
G_T = 200*mmolar            # Total vesicular gliotransmitter concentration
rho_e = 6.5e-4              # Astrocytic vesicle-to-extracellular volume ratio
Omega_e = 60/second         # Gliotransmitter clearance rate
alpha = 0.0                 # Gliotransmission nature
##############################################################################
seed(16283) 
#Neurons
rate_in = TimedArray([0.011, 0.11, 1.1, 11]*Hz, dt=5*second)
pre_synaptic = PoissonGroup(N_syn, rates='rate_in(t)')
post_synaptic = NeuronGroup(N_syn, model="")

#Synapses
syn_eqs = """
du_S/dt = -Omega_f * u_S                           : 1 (clock-driven)
dx_S/dt = Omega_d * (1-x_S)                        : 1 (clock-driven)
dY_S/dt = -Omega_c*Y_S                             : mmolar (clock-driven)
dGamma_S/dt = O_G*G_A*(1-Gamma_S)-Omega_G*Gamma_S  : 1 (clock-driven)
G_A                                                : mmolar
r_S                                                : 1
"""
syn_action = """
U_0 = (1 - Gamma_S) * U_0__star + alpha * Gamma_S
u_S += U_0 * (1 - u_S)
r_S = u_S * x_S
x_S -= r_S
Y_S += rho_c * Y_T * r_S
"""

synapses = Synapses(pre_synaptic, post_synaptic, model=syn_eqs, on_pre=syn_action, method='linear')
synapses.connect(j='i')
synapses.connect(j='i')
synapses.x_S = 1.0

#Astrocyte
astro_eqs = """
# Fraction of activated astrocyte receptors (1):
dGamma_A/dt = O_N * Y_S * (1 - Gamma_A) -
            Omega_N*(1 + zeta * C/(C + K_KC)) * Gamma_A : 1

# IP_3 dynamics (1):
dI/dt = J_beta + J_delta - J_3K - J_5P       : mmolar

J_beta = O_beta * Gamma_A                         : mmolar/second
J_delta = O_delta/(1 + I/kappa_delta) *
                        C**2/(C**2 + K_delta**2) : mmolar/second
J_3K = O_3K * C**4/(C**4 + K_D**4) * I/(I + K_3K) : mmolar/second
J_5P = Omega_5P*I                                 : mmolar/second

# Calcium dynamics (2):
dC/dt = J_r + J_l - J_p: mmolar
dh/dt = (h_inf - h) / tau_h: 1

J_r = Omega_C*(m_inf**3)*(h**3)*(C_T-(1+rho_A)*C)  : mmolar/second
J_l = Omega_L*(C_T-(1+rho_A)*C)                    : mmolar/second
J_p = (O_P*C**2)/(K_P**2+C**2)                     : mmolar/second

Q_2 = d_2*((I+d_1)/(I+d_3))                  : mmolar
m_inf = (I/(I+d_1))*(C/(C+d_5))              : 1
tau_h = 1 / (O_2*(Q_2+C))                    : second
h_inf = Q_2/(Q_2+C)                          : 1


# Fraction of gliotransmitter resources available for release
dx_A/dt = Omega_A * (1 - x_A) : 1

# gliotransmitter concentration in the extracellular space
dG_A/dt = -Omega_e*G_A        : mmolar

# Neurotransmitter concentration in the extracellular space
Y_S     : mmolar
"""

astro_release = """
G_A += rho_e*G_T*U_A*x_A
"""

astrocyte = NeuronGroup(N_a*N_syn, model=astro_eqs, method='rk4',
                        threshold='C>C_Theta', refractory='C>C_Theta', reset='G_A += rho_e*G_T*U_A*x_A')
astrocyte.x_A = 1.0
astrocyte.h = 0.9
astrocyte.I = 0.4*umolar

#Closed-loop
ecs_syn_to_astro = Synapses(synapses, astrocyte, 
                            model='Y_S_post = Y_S_pre : mmolar (summed)')
ecs_syn_to_astro.connect(j='i if i<N_syn')

ecs_astro_to_syn = Synapses(astrocyte, synapses,
                            model='G_A_post = G_A_pre : mmolar (summed)')
ecs_astro_to_syn.connect(j='i if i<N_syn')



#Monitor
syn_mon = StateMonitor(synapses, ['Y_S', 'Gamma_S'], record=True)
astro_mon = StateMonitor(astrocyte, 'G_A', record=True)

run(duration, report='text')
# print(syn_mon.Y_S[:N_syn].shape)
# print(len(syn_mon.Y_S.mean(axis=0)))

# Plots
fig1 = plt.figure(num=f'Average synaptic Neurotrasmitter, alpha:{alpha}',figsize=(10,10))
ax11 = fig1.add_subplot(3,1,1)
ax12 = fig1.add_subplot(3,1,2)
ax13 = fig1.add_subplot(3,1,3)

ax11.semilogy(syn_mon.t, rate_in(syn_mon.t), '-', color='black')
ax11.set_ylabel(r'$\nu_{in}$ (Hz)')
ax11.grid(linestyle='dotted')

ax12.plot(syn_mon.t[:], syn_mon.Y_S[N_syn:].mean(axis=0)/umolar, color='C2', label='no gliotrasmission')
ax12.set_ylabel(r'$\langle Y_S \rangle$  ($\mu$M)')
ax12.legend()
ax12.grid(linestyle='dotted')

ax13.plot(syn_mon.t[:], syn_mon.Y_S[:N_syn].mean(axis=0)/umolar, color='C3', label='gliotrasmission')
ax13.set_ylabel(r'$\langle Y_S \rangle$  ($\mu$M)')
ax13.set_xlabel('time (s)')
ax13.legend()
ax13.grid(linestyle='dotted')

fig2 = plt.figure(num=f'Gliotrasmitter release, alpha:{alpha}',figsize=(10,5))
ax21 = fig2.add_subplot(2,1,1)
ax22 = fig2.add_subplot(2,1,2)

ax21.plot(astro_mon.t[:], astro_mon.G_A.mean(axis=0), label='average GRE')
ax21.set_ylabel(r'$\langle G_A \rangle$  ($\mu$M)')
ax21.legend()
ax21.grid(linestyle='dotted')

ax22.plot(syn_mon.t[:], syn_mon.Gamma_S[:N_syn].mean(axis=0), label=r'average $\Gamma_S$')
ax22.set_ylabel(r'$\langle \Gamma_S \rangle$  ($\mu$M)')
ax22.set_xlabel('time (s)')
ax22.legend()
ax22.grid(linestyle='dotted')

# Connectivity_plot(synapses, source='pre_syn', target='post_syn', color_s='b', color_t='b', size=2)
# Connectivity_plot(ecs_syn_to_astro, source='synapse', target='astrocyte', color_s='b', color_t='b', size=2)
# Connectivity_plot(ecs_astro_to_syn, source='astrocyte', target='synapse', color_s='b', color_t='b', size=2)

plt.show()