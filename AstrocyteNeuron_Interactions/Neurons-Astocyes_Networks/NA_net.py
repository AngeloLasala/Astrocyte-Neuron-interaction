"""
coupling neurons and astrocyte network

Randomly connected COBA network  with excitatory synapses modulated
by release-increasing gliotransmission from a connected network of astrocytes.

- "Modelling neuro-glia interactions with the Brian2 simulator" Stimberg et al (2017)
"""
import numpy as np
import matplotlib.pyplot as plt
from brian2 import *
from AstrocyteNeuron_Interactions.Brian2_tutorial.connectivity import Connectivity_plot

if __name__ == '__main__': 
    
    ## PARAMETERS ###################################################################
    # --  General parameters --
    N_e = 20                    # Number of excitatory neurons
    N_i = 5                     # Number of inhibitory neurons
    N_a = 20                    # Number of astrocytes

    # -- Some metrics parameters needed to establish proper connections --
    size = 3.75*mmeter           # Length and width of the square lattice
    distance = 50*umeter         # Distance between neurons

    # -- Neuron --
    E_l = -60*mV                 # Leak reversal potential
    g_l = 9.99*nS                # Leak conductance
    E_e = 0*mV                   # Excitatory synaptic reversal potential
    E_i = -80*mV                 # Inhibitory synaptic reversal potential
    C_m = 198*pF                 # Membrane capacitance
    tau_e = 5*ms                 # Excitatory synaptic time constant
    tau_i = 10*ms                # Inhibitory synaptic time constant
    tau_r = 5*ms                 # Refractory period
    I_ex = 100*pA                # External current
    V_th = -50*mV                # Firing threshold
    V_r = E_l                    # Reset potential

    # -- Synapse --
    rho_c = 0.005                # Synaptic vesicle-to-extracellular space volume ratio
    Y_T = 500.*mmolar            # Total vesicular neurotransmitter concentration
    Omega_c = 40/second          # Neurotransmitter clearance rate
    U_0__star = 0.6              # Resting synaptic release probability
    Omega_f = 3.33/second        # Synaptic facilitation rate
    Omega_d = 2.0/second         # Synaptic depression rate
    w_e = 0.05*nS                # Excitatory synaptic conductance
    w_i = 1.0*nS                 # Inhibitory synaptic conductance
    # - Presynaptic receptors
    O_G = 1.5/umolar/second      # Agonist binding (activating) rate
    Omega_G = 0.5/(60*second)    # Agonist release (deactivating) rate

    # -- Astrocyte --
    # CICR
    O_P = 0.9*umolar/second      # Maximal Ca^2+ uptake rate by SERCAs
    K_P = 0.05*umolar            # Ca2+ affinity of SERCAs
    C_T = 2*umolar               # Total cell free Ca^2+ content
    rho_A = 0.18                 # ER-to-cytoplasm volume ratio
    Omega_C = 6/second           # Maximal rate of Ca^2+ release by IP_3Rs
    Omega_L = 0.1/second         # Maximal rate of Ca^2+ leak from the ER
    d_1 = 0.13*umolar            # IP_3 binding affinity
    d_2 = 1.05*umolar            # Ca^2+ inactivation dissociation constant
    O_2 = 0.2/umolar/second      # IP_3R binding rate for Ca^2+ inhibition
    d_3 = 0.9434*umolar          # IP_3 dissociation constant
    d_5 = 0.08*umolar            # Ca^2+ activation dissociation constant
    #  IP_3 production
    # Agonist-dependent IP_3 production
    O_beta = 0.5*umolar/second   # Maximal rate of IP_3 production by PLCbeta
    O_N = 0.3/umolar/second      # Agonist binding rate
    Omega_N = 0.5/second         # Maximal inactivation rate
    K_KC = 0.5*umolar            # Ca^2+ affinity of PKC
    zeta = 10                    # Maximal reduction of receptor affinity by PKC
    # Endogenous IP3 production
    O_delta = 1.2*umolar/second  # Maximal rate of IP_3 production by PLCdelta
    kappa_delta = 1.5*umolar     # Inhibition constant of PLC_delta by IP_3
    K_delta = 0.1*umolar         # Ca^2+ affinity of PLCdelta
    # IP_3 degradation
    Omega_5P = 0.05/second       # Maximal rate of IP_3 degradation by IP-5P
    K_D = 0.7*umolar             # Ca^2+ affinity of IP3-3K
    K_3K = 1.0*umolar            # IP_3 affinity of IP_3-3K
    O_3K = 4.5*umolar/second     # Maximal rate of IP_3 degradation by IP_3-3K
    # IP_3 diffusion (astrocyte coupling)
    F = 0.09*umolar/second       # GJC IP_3 permeability
    I_Theta = 0.3*umolar         # Threshold gradient for IP_3 diffusion
    omega_I = 0.05*umolar        # Scaling factor of diffusion
    # Gliotransmitter release and time course
    C_Theta = 0.5*umolar         # Ca^2+ threshold for exocytosis
    Omega_A = 0.6/second         # Gliotransmitter recycling rate
    U_A = 0.6                    # Gliotransmitter release probability
    G_T = 200*mmolar             # Total vesicular gliotransmitter concentration
    rho_e = 6.5e-4               # Astrocytic vesicle-to-extracellular volume ratio
    Omega_e = 60/second          # Gliotransmitter clearance rate
    alpha = 0.0                  # Gliotransmission nature
    ################################################################################

    dt_stim = 2*second
    stimulus = TimedArray([1.0,1.0,1.2,1.0], dt=dt_stim)
    duration = 4*dt_stim

    defaultclock.dt = 0.1*ms
    seed(14568)

    ## NEURONS 
    neuron_eqs = """
    # Neurons dynamics
    dv/dt = (g_l*(E_l-v) + g_e*(E_e-v) + g_i*(E_i-v) + I_ex*stimulus(t))/C_m : volt (unless refractory)
    dg_e/dt = -g_e/tau_e : siemens  # post-synaptic excitatory conductance
    dg_i/dt = -g_i/tau_i : siemens  # post-synaptic inhibitory conductance
    
    # Neuron position in space
    x : meter (constant)
    y : meter (constant)
    """

    neurons = NeuronGroup(N_e+N_i, model=neuron_eqs, method='rk4',
                     threshold='v>V_th', reset='v=V_r', refractory='tau_r')

    exc_neurons = neurons[:N_e]
    inh_neurons = neurons[N_e:]

    # Arrange excitatory neurons in a grid
    N_rows_exc = int(sqrt(N_e))
    N_cols_exc = N_e/N_rows_exc
    grid_dist = (size / N_cols_exc)
    print(f'dist neurons = {grid_dist}')
    #square grid
    x = np.arange(N_rows_exc)
    y = np.arange(N_cols_exc)
    XX,YY = np.meshgrid(x,y)

    exc_neurons.x = XX.flatten()[:N_e]*grid_dist
    exc_neurons.y = YY.flatten()[:N_e]*grid_dist
    # exc_neurons.x = '(i / N_rows_exc)*grid_dist - N_rows_exc/2.0*grid_dist'
    # exc_neurons.y = '(i % N_rows_exc)*grid_dist - N_cols_exc/2.0*grid_dist'
    
    # Random initial membrane potential values and conductances
    neurons.v = 'E_l + rand()*(V_th-E_l)'
    neurons.g_e = 'rand()*w_e'
    neurons.g_i = 'rand()*w_i'

    # SYNAPSE
    #Synapses
    syn_model = """
    du_S/dt = -Omega_f * u_S                           : 1 (clock-driven)
    dx_S/dt = Omega_d * (1-x_S)                        : 1 (clock-driven)
    dY_S/dt = -Omega_c*Y_S                             : mmolar (clock-driven)
    dGamma_S/dt = O_G*G_A*(1-Gamma_S)-Omega_G*Gamma_S  : 1 (clock-driven)
    G_A                                                : mmolar
    r_S                                                : 1

    # which astrocyte covers this synapse ?
    astrocyte_index : integer (constant)
    """

    syn_action = """
    U_0 = (1 - Gamma_S) * U_0__star + alpha * Gamma_S
    u_S += U_0 * (1 - u_S)
    r_S = u_S * x_S
    x_S -= r_S
    Y_S += rho_c * Y_T * r_S
    """

    exc="g_e_post+=w_e*r_S"

    inh="g_i_post+=w_i*r_S"

    exc_syn = Synapses(exc_neurons, neurons, model= syn_model, on_pre=syn_action+exc, method='linear')
    inh_syn = Synapses(inh_neurons, neurons, model= syn_model, on_pre=syn_action+inh, method='linear')
    exc_syn.connect(True, p=0.05)
    inh_syn.connect(True, p=0.2)

    exc_syn.x_S = 1
    inh_syn.x_S = 1

    # Connect excitatory synapses to an astrocyte depending on the position of the
    # post-synaptic neuron
    N_rows_astro = int(sqrt(N_a))
    N_cols_astro = N_e/N_rows_astro
    grid_dist = (size / N_cols_astro)
    exc_syn.astrocyte_index = ('int(x_post/grid_dist) + '
                               'N_cols_astro*int(y_post/grid_dist)')
    print(grid_dist)
    print(np.array(exc_syn.x_post)/grid_dist)
    print(np.array(exc_syn.y_post)/grid_dist)
    print(np.array(exc_syn.astrocyte_index))

    # ASTROCYTE
    astro_eqs = """
    # Fraction of activated astrocyte receptors (1):
    dGamma_A/dt = O_N * Y_S * (1 - clip(Gamma_A,0,1)) -
                  Omega_N*(1 + zeta * C/(C + K_KC)) * clip(Gamma_A,0,1) : 1

    Gamma_A_c = clip(Gamma_A,0,1)   : 1

    # IP_3 dynamics (1):
    dI/dt = J_beta + J_delta - J_3K - J_5P       : mmolar

    J_beta = O_beta * Gamma_A_c                                       : mmolar/second
    J_delta = O_delta/(1 + I/kappa_delta) * C**2/(C**2 + K_delta**2) : mmolar/second
    J_3K = O_3K * C**4/(C**4 + K_D**4) * I/(I + K_3K)                : mmolar/second
    J_5P = Omega_5P*I                                                : mmolar/second

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

    # The astrocyte position in space
    x : meter (constant)
    y : meter (constant)

    """

    astro_release = """
    G_A += rho_e*G_T*U_A*x_A
    x_A -= U_A * x_A
    """

    astrocyte = NeuronGroup(N_a, model=astro_eqs, method='rk4',
                            threshold='C>C_Theta', refractory='C>C_Theta', reset=astro_release, dt=1e-2*second)

    # Arrange excitatory neurons in a grid
    #square grid
    x_astro = np.arange(N_rows_astro)
    y_astro = np.arange(N_cols_astro)
    XX_A,YY_A = np.meshgrid(x_astro,y_astro)

    astrocyte.x = XX_A.flatten()[:N_a]*grid_dist
    astrocyte.y = YY_A.flatten()[:N_a]*grid_dist
    # astrocyte.x = '(i / N_rows_astro)*grid_dist - N_rows_astro/2.0*grid_dist'
    # astrocyte.y = '(i % N_rows_astro)*grid_dist - N_cols_astro/2.0*grid_dist'

    
    astrocyte.C =0.01*umolar
    astrocyte.h = 0.9
    astrocyte.I = 0.01*umolar
    astrocyte.x_A = 1.0

    # bidirectional connection beetwith astrocyte and excitatory synapses
    # based on postsynaptic neurons position
    # ASTRO TO EXC_SYNAPSES
    ecs_astro_to_syn = Synapses(astrocyte, exc_syn, 'G_A_post = G_A_pre : mmolar (summed)')
    ecs_astro_to_syn.connect('i == astrocyte_index_post')

    #EXC_SYNAPSES TO ASTRO
    ecs_syn_to_astro = Synapses(exc_syn, astrocyte, 'Y_S_post = Y_S_pre : mmolar (summed)')
    ecs_syn_to_astro.connect('astrocyte_index_pre == j')

    #MOMITOR
    spikes_exc_mon = SpikeMonitor(exc_neurons)
    spikes_inh_mon = SpikeMonitor(inh_neurons)
    astro_mon = SpikeMonitor(astrocyte)
    avar_mon = StateMonitor(astrocyte, ['C','I','h','Gamma_A','Y_S','G_A','x_A','Gamma_A_c'], record=True)

    run(duration, report='text')

    print('NETWORK INFORMATION')
    print(f'excitatory neurons = {N_e}')
    print(f'inhibitory neurons = {N_i}')
    print(f'excitatory synapses = {len(exc_syn.i)}')
    print(f'inhibitory synapses = {len(inh_syn.i)}')
    print('_______________\n')
    print(f'astrocytes = {N_a}')
    print(f'syn to astro connection = {len(ecs_syn_to_astro.i)}')
    print(f'astro to syn connection = {len(ecs_astro_to_syn.i)}\n\n')

    

    #Plots
    fig1 = plt.figure(num=f'Raster plot, Ne:{N_e} Ni:{N_i}, Iex={I_ex/pA}', figsize=(12,12))
    ax11 = fig1.add_subplot(1,1,1)

    step = 5
    ax11.scatter(spikes_exc_mon.t[np.array(spikes_exc_mon.i)%step==0], 
                spikes_exc_mon.i[np.array(spikes_exc_mon.i)%step==0], color='C3', marker='|')
    ax11.scatter(spikes_inh_mon.t[np.array(spikes_inh_mon.i)%step==0], 
                spikes_inh_mon.i[np.array(spikes_inh_mon.i)%step==0]+N_e, color='C0', marker='|')
    ax11,scatter(astro_mon.t[np.array(astro_mon.i)%step==0], 
                astro_mon.i[np.array(astro_mon.i)%step==0]+N_e+N_i, color='green', marker='|')
    ax11.set_xlabel('time (s)')
    ax11.set_ylabel('cell index')

    fig2 = plt.figure(num='astrocyte dynamics', figsize=(12,12))
    ax21 = fig2.add_subplot(7,1,1)
    ax22 = fig2.add_subplot(7,1,2)
    ax23 = fig2.add_subplot(7,1,3)
    ax24 = fig2.add_subplot(7,1,4)
    ax25 = fig2.add_subplot(7,1,5)
    ax26 = fig2.add_subplot(7,1,6)
    ax27 = fig2.add_subplot(7,1,7)

    index_plot = 0
    ax21.plot(avar_mon.t[:], avar_mon.Y_S[index_plot]/umolar, color='C3')
    ax21.set_ylabel(r'$Y_S$ ($\mu$M)')
    ax21.grid(linestyle='dotted')

    ax22.plot(avar_mon.t[:], avar_mon.Gamma_A_c[index_plot], color='C4')
    ax22.plot(avar_mon.t[:], avar_mon.Gamma_A[index_plot], color='C7')
    ax22.set_ylabel(r'$\Gamma_A$ ')
    ax22.grid(linestyle='dotted')

    ax23.plot(avar_mon.t[:], avar_mon.I[index_plot]/umolar, color='C5')
    ax23.set_ylabel(r'$I$ ($\mu$M)')
    ax23.grid(linestyle='dotted')

    ax24.plot(avar_mon.t[:], avar_mon.C[index_plot]/umolar, color='red')
    ax24.set_ylabel(r'$Ca^{2\plus}$ ($\mu$M)')
    ax24.axhline(C_Theta/umolar,0,duration/second, ls='dashed', color='black')
    ax24.grid(linestyle='dotted')

    ax25.plot(avar_mon.t[:], avar_mon.h[index_plot], color='C6')
    ax25.set_ylabel(r'$h$')
    ax25.grid(linestyle='dotted')

    ax26.plot(avar_mon.t[:], avar_mon.G_A[index_plot], color='C7')
    ax26.set_ylabel(r'$G_A$')
    ax26.grid(linestyle='dotted')

    ax27.plot(avar_mon.t[:], avar_mon.x_A[index_plot], color='C8')
    ax27.set_ylabel(r'$x_A$')
    ax27.grid(linestyle='dotted')

    # Connectivity_plot(exc_syn, source='Exc', target='Exc+Inh', color_s='red', color_t='indigo', size=10, name='exc syn')
    # Connectivity_plot(inh_syn, source='Inh', target='Exc+Inh', color_s='C0', color_t='indigo', size=10)
    # Connectivity_plot(ecs_astro_to_syn, source='Astro', target='Exc syn', color_s='green', color_t='red', size=10, name='stro_to_syn')
    # Connectivity_plot(ecs_syn_to_astro, source='Exc syn', target='Astro', color_s='red', color_t='green', size=10, name='syn_to_astro')


    # plt.figure(num='N_e grid')
    # plt.scatter(exc_neurons.x/mmeter, exc_neurons.y/mmeter)
    # plt.scatter(exc_syn.x_pre/mmeter, exc_syn.y_pre/mmetre, label='pre')
    # plt.legend()

    # plt.figure(num='N_e grid_1')
    # plt.scatter(exc_neurons.x/mmeter, exc_neurons.y/mmeter)
    # plt.scatter(exc_syn.x_post/mmeter, exc_syn.y_post/mmetre, label='post')
    # plt.legend()


    # plt.figure(num='Astro grid')
    # plt.scatter(astrocyte.x/mmeter, astrocyte.y/mmeter)
    # plt.legend()

   
    plt.show()
