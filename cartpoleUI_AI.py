import argparse

import matplotlib
import pygame
from pygame.locals import K_RIGHT, K_LEFT, KEYDOWN, KEYUP
from stable_baselines3 import PPO

import gym
from gym import logger

try:
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
except ImportError as e:
    logger.warn(f"failed to set matplotlib backend, plotting will not work: {str(e)}")
    plt = None

from collections import deque

from pygame.locals import VIDEORESIZE


def display_arr(screen, arr, video_size, transpose):
    arr_min, arr_max = arr.min(), arr.max()
    arr = 255.0 * (arr - arr_min) / (arr_max - arr_min)
    pyg_img = pygame.surfarray.make_surface(arr.swapaxes(0, 1) if transpose else arr)
    pyg_img = pygame.transform.scale(pyg_img, video_size)
    screen.blit(pyg_img, (0, 0))

def get_AI_prediction(model, obs):
    action, _ = model.predict(obs)
    model.policy.set_training_mode(False)
    observation, vectorized_env = model.policy.obs_to_tensor(obs)
    action_distribution = model.policy.get_distribution(observation)
    action_probs = action_distribution.distribution.probs.detach().numpy()
    return action, action_probs


def play(env, transpose=True, fps=30, zoom=None, callback=None, keys_to_action=None, model=None):
    """Allows one to play the game using keyboard.
    To simply play the game use:
        play(gym.make("Pong-v4"))
    Above code works also if env is wrapped, so it's particularly useful in
    verifying that the frame-level preprocessing does not render the game
    unplayable.
    If you wish to plot real time statistics as you play, you can use
    gym.utils.play.PlayPlot. Here's a sample code for plotting the reward
    for last 5 second of gameplay.
        def callback(obs_t, obs_tp1, action, rew, done, info):
            return [rew,]
        plotter = PlayPlot(callback, 30 * 5, ["reward"])
        env = gym.make("Pong-v4")
        play(env, callback=plotter.callback)
    Arguments
    ---------
    env: gym.Env
        Environment to use for playing.
    transpose: bool
        If True the output of observation is transposed.
        Defaults to true.
    fps: int
        Maximum number of steps of the environment to execute every second.
        Defaults to 30.
    zoom: float
        Make screen edge this many times bigger
    callback: lambda or None
        Callback if a callback is provided it will be executed after
        every step. It takes the following input:
            obs_t: observation before performing action
            obs_tp1: observation after performing action
            action: action that was executed
            rew: reward that was received
            done: whether the environment is done or not
            info: debug info
    keys_to_action: dict: tuple(int) -> int or None
        Mapping from keys pressed to action performed.
        For example if pressed 'w' and space at the same time is supposed
        to trigger action number 2 then key_to_action dict would look like this:
            {
                # ...
                sorted(ord('w'), ord(' ')) -> 2
                # ...
            }
        If None, default key_to_action mapping for that env is used, if provided.
    """
    env.reset()
    rendered = env.render(mode="rgb_array")

    if keys_to_action is None:
        if hasattr(env, "get_keys_to_action"):
            keys_to_action = env.get_keys_to_action()
        elif hasattr(env.unwrapped, "get_keys_to_action"):
            keys_to_action = env.unwrapped.get_keys_to_action()
        else:
            assert False, (
                env.spec.id
                + " does not have explicit key to action mapping, "
                + "please specify one manually"
            )
    # relevant_keys = set(keys_to_action.keys())
    relevant_keys = set(sum(map(list, keys_to_action.keys()), []))

    video_size = [rendered.shape[1], rendered.shape[0]]
    if zoom is not None:
        video_size = int(video_size[0] * zoom), int(video_size[1] * zoom)

    pressed_keys = []
    running = True
    env_done = True
    pygame.init()
    screen = pygame.display.set_mode(video_size)
    clock = pygame.time.Clock()

    while running:

        action = cartPos = cartVel = poleAng = poleVel = 0
        
        if env_done:
            env_done = False
            obs = env.reset()
        else:
            # suggestions from AI
            if model is not None:
                action_AI, action_prob_AI = get_AI_prediction(model, obs)

            print("pressed_keys", pressed_keys)
            action = keys_to_action.get(tuple(sorted(pressed_keys)), 0)
            print("ACTION: ", action)
            prev_obs = obs
            cartPos, cartVel, poleAng, poleVel = obs
            obs, rew, env_done, info = env.step(action)
            if callback is not None:
                callback(prev_obs, obs, action, rew, env_done, info)
        if obs is not None:
            rendered = env.render(mode="rgb_array")
            display_arr(screen, rendered, transpose=transpose, video_size=video_size)

        #Display Non Active Arrows as gray
        pygame.draw.polygon(screen, "gray", ((300, 50), (300, 100), (200, 100), (200, 150), (150, 75), (200, 0), (200, 50)))
        pygame.draw.polygon(screen, "gray", ((300, 50), (300, 100), (400, 100), (400, 150), (450, 75), (400, 0), (400, 50)))      
        #### Display current Action Arrow
        if (action == 0):
            pygame.draw.polygon(screen, "red", ((300, 50), (300, 100), (200, 100), (200, 150), (150, 75), (200, 0), (200, 50)))
        elif (action == 1):
            pygame.draw.polygon(screen, "red", ((300, 50), (300, 100), (400, 100), (400, 150), (450, 75), (400, 0), (400, 50)))
        ####

        #### Display Probability of Each Action
        probLeft = 56
        probRight = 44
        font = pygame.font.Font(None, 45)
        txtLeft = font.render(str(probLeft) + "%", True, "black")
        txtRight = font.render(str(probRight) + "%", True, "black")
        screen.blit(txtLeft, (225,63))
        screen.blit(txtRight, (315,63))

        #### Display Observations
        font = pygame.font.Font(None, 25)
        txtCartPos = font.render("Cart Position: " + str(cartPos) , True, "black")
        txtCartVel = font.render("Cart Velocity: " + str(cartVel) , True, "black")
        txtPoleAng = font.render("Pole Angle: " + str(poleAng) , True, "black")
        txtPoleVel = font.render("Pole Velocity: " + str(poleVel) , True, "black")
        offset = 160
        screen.blit(txtCartPos, (0,offset))
        screen.blit(txtCartVel, (0,offset + 25))
        screen.blit(txtPoleAng, (0,offset + 50))
        screen.blit(txtPoleVel, (0,offset + 75))
        #print("Cart Position: " + str(cartPos))
        #print("Cart Velocity: " + str(cartVel))
        #print("Pole Angle: " + str(poleAng))
        #print("Pole Velocity: " + str(poleVel))

        # process pygame events
        for event in pygame.event.get():
            # test events, set key states
            if event.type == pygame.KEYDOWN:
                if event.key in relevant_keys:
                    pressed_keys.append(event.key)
                elif event.key == 27:
                    running = False
            elif event.type == pygame.KEYUP:
                if event.key in relevant_keys:
                    pressed_keys.remove(event.key)
            elif event.type == pygame.QUIT:
                running = False
            elif event.type == VIDEORESIZE:
                video_size = event.size
                screen = pygame.display.set_mode(video_size)
                print(video_size)

        pygame.display.flip()
        clock.tick(fps)
    pygame.quit()


class PlayPlot:
    def __init__(self, callback, horizon_timesteps, plot_names):
        self.data_callback = callback
        self.horizon_timesteps = horizon_timesteps
        self.plot_names = plot_names

        assert plt is not None, "matplotlib backend failed, plotting will not work"

        num_plots = len(self.plot_names)
        self.fig, self.ax = plt.subplots(num_plots)
        if num_plots == 1:
            self.ax = [self.ax]
        for axis, name in zip(self.ax, plot_names):
            axis.set_title(name)
        self.t = 0
        self.cur_plot = [None for _ in range(num_plots)]
        self.data = [deque(maxlen=horizon_timesteps) for _ in range(num_plots)]

    def callback(self, obs_t, obs_tp1, action, rew, done, info):
        points = self.data_callback(obs_t, obs_tp1, action, rew, done, info)
        for point, data_series in zip(points, self.data):
            data_series.append(point)
        self.t += 1

        xmin, xmax = max(0, self.t - self.horizon_timesteps), self.t

        for i, plot in enumerate(self.cur_plot):
            if plot is not None:
                plot.remove()
            self.cur_plot[i] = self.ax[i].scatter(
                range(xmin, xmax), list(self.data[i]), c="blue"
            )
            self.ax[i].set_xlim(xmin, xmax)
        plt.pause(0.000001)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env",
        type=str,
        default="CartPole-v1",
        help="Define Environment",
    )
    args = parser.parse_args()
    env = gym.make(args.env)
    model = PPO.load("CartPole-v1", env=env, verbose=1)

    play(env, zoom=1, fps=10,
         keys_to_action={
             (K_LEFT,): 0,
             (K_RIGHT,): 1
         },
         model=model
         )


if __name__ == "__main__":
    main()