# import lasagne
# import lasagne.layers as L
# import lasagne.nonlinearities as NL
# import lasagne.init as LI
from rllab.core.serializable import Serializable
from rllab.misc import ext
from rllab.misc.overrides import overrides
from sandbox.rocky.tf.core.layers_powered import LayersPowered
from sandbox.rocky.tf.core.network import MLP
from hierarchical_network import HierarchicalMLP
from sandbox.rocky.tf.distributions.categorical import Categorical
from sandbox.rocky.tf.policies.base import Policy
from sandbox.rocky.tf.misc import tensor_utils

import sandbox.rocky.tf.core.layers as L
from sandbox.rocky.tf.core.layers import batch_norm
from sandbox.rocky.tf.spaces.discrete import Discrete
import tensorflow as tf


class LayeredDeterministicMLPPolicy(Policy, LayersPowered, Serializable):
    def __init__(
            self,
            name,
            env_spec,
            hidden_sizes=(32, 32),
            hidden_nonlinearity=tf.nn.relu,
            output_nonlinearity=tf.nn.tanh,
            output_nonlinearity_binary=tf.nn.sigmoid,
            output_dim_binary=1,
            prob_network=None,
            bn=False):
        Serializable.quick_init(self, locals())


        with tf.variable_scope(name):
            if prob_network is None:
                
                prob_network = HierarchicalMLP(
                    input_shape=(env_spec.observation_space.flat_dim,),
                    output_dim=env_spec.action_space.flat_dim,
                    hidden_sizes=hidden_sizes,
                    hidden_nonlinearity=hidden_nonlinearity,
                    output_nonlinearity=output_nonlinearity,
                    output_nonlinearity_binary=output_nonlinearity_binary,
                    output_dim_binary=output_dim_binary, 
                    # batch_normalization=True,
                    name="prob_network",
                )

            self._l_prob = prob_network.output_layer
            self._l_obs = prob_network.input_layer
            self._f_prob = tensor_utils.compile_function(
                [prob_network.input_layer.input_var],
                L.get_output(prob_network.output_layer, deterministic=True)
            )

            self._f_prob_binary = tensor_utils.compile_function(
                [prob_network.input_layer.input_var],
                L.get_output(prob_network.output_layer_binary, deterministic=True)
            )


        self.output_layer_binary = prob_network.output_layer_binary
        self.binary_output = L.get_output(prob_network.output_layer_binary, deterministic=True)

        self.prob_network = prob_network

        # Note the deterministic=True argument. It makes sure that when getting
        # actions from single observations, we do not update params in the
        # batch normalization layers.
        # TODO: this doesn't currently work properly in the tf version so we leave out batch_norm
        super(LayeredDeterministicMLPPolicy, self).__init__(env_spec)
        LayersPowered.__init__(self, [prob_network.output_layer, prob_network.output_layer_binary])
        # LayersPowered.__init__(self, [prob_network.output_layer_binary])
        


    @property
    def vectorized(self):
        return True
        
    @overrides
    def get_action(self, observation):
        flat_obs = self.observation_space.flatten(observation)

        #get continuous action output
        action = self._f_prob([flat_obs])[0]

        #get discrete action output - sigmoid probability in this case
        binary_action = self._f_prob_binary([flat_obs])[0]# tf.reshape(self.prob_network.output_binary, [-1])

        return action, binary_action, dict()



    @overrides
    def get_actions(self, observations):
        flat_obs = self.observation_space.flatten_n(observations)
 
        import pdb; pdb.set_trace()

        actions = self._f_prob(flat_obs)
        
        binary_action = self._f_prob_binary([flat_obs])[0]


        return actions, binary_action, dict()




    def get_action_sym(self, obs_var):
        return L.get_output(self.prob_network.output_layer, obs_var)
