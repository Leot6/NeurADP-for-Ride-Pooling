from Environment import NYEnvironment
from CentralAgent import CentralAgent
from LearningAgent import LearningAgent
from Oracle import Oracle
from ValueFunction import PathBasedNN

from typing import List

import pdb


def run_epoch(envt,
              oracle,
              central_agent,
              value_function,
              NUM_AGENTS,
              DAY,
              START_HOUR,
              END_HOUR,
              is_training):

    # Initialising agents
    agents: List[LearningAgent] = []
    for agent_idx, initial_state in enumerate(envt.get_initial_state(NUM_AGENTS)):
        agent = LearningAgent(agent_idx, initial_state)
        agents.append(agent)

    # Iterating over episode
    request_generator = envt.get_request_batch(START_HOUR, END_HOUR, DAY)

    total_value_generated = 0
    num_total_requests = 0
    while True:
        # Get new requests
        try:
            current_requests = next(request_generator)
            print("Current time: {}".format(envt.current_time))
            print("Number of new requests: {}".format(len(current_requests)))
        except StopIteration:
            break

        # Get feasible actions and score them
        print("Generating feasible requests...")
        # feasible_request_combinations = oracle.get_request_combinations(current_requests)
        scored_actions_all_agents = []
        for agent_idx in range(NUM_AGENTS):
            feasible_actions = oracle.get_feasible_actions(agents[agent_idx], current_requests)
            scored_actions = value_function.get_value(agents[agent_idx], feasible_actions, envt.current_time)
            scored_actions_all_agents.append(scored_actions)

        # Choose actions for each agent
        print("Choosing best actions...")
        final_actions = central_agent.choose_actions(scored_actions_all_agents, is_training)
        for agent_idx, action in enumerate(final_actions):
            agents[agent_idx].path = action.new_path

        # Get reward
        rewards = []
        for action in final_actions:
            reward = envt.get_reward(action)
            rewards.append(reward)
            total_value_generated += reward
        print("Reward for epoch: {}".format(sum(rewards)))

        # Update value function
        if (is_training):
            print("Updating value function...")
            feasible_actions_all_agents = [[action for action, _ in scored_actions] for scored_actions in scored_actions_all_agents]
            is_terminal = (END_HOUR * 3600) - envt.EPOCH_LENGTH == envt.current_time
            value_function.update(agents, final_actions, feasible_actions_all_agents, is_terminal)

        # Sanity check
        print("Sanity check...")
        for agent in agents:
            assert envt.has_valid_path(agent)

        # Simulate the passing of time
        print("Simulating motion till next epoch...")
        envt.simulate_motion(agents, current_requests)

        # Printing statistics for current epoch
        num_total_requests += len(current_requests)
        print('Number of requests accepted: {}'.format(total_value_generated))
        print('Number of requests seen: {}'.format(num_total_requests))
        print()

    return total_value_generated


if __name__ == '__main__':
    # pdb.set_trace()

    # Constants
    NUM_AGENTS: int = 1000
    START_HOUR: int = 8
    END_HOUR: int = 9
    NUM_EPOCHS: int = 100
    TRAINING_DAYS: List[int] = [3, 4, 5, 6]
    TEST_DAY: int = 2

    # Initialising components
    envt = NYEnvironment()
    oracle = Oracle(envt)
    central_agent = CentralAgent()
    value_function = PathBasedNN(envt)

    for epoch_id in range(NUM_EPOCHS):
        for day in TRAINING_DAYS:
            total_requests_served = run_epoch(envt, oracle, central_agent, value_function, NUM_AGENTS, day, START_HOUR, END_HOUR, is_training=True)
            print("DAY: {}, Requests: {}".format(day, total_requests_served))

        total_requests_served = run_epoch(envt, oracle, central_agent, value_function, NUM_AGENTS, TEST_DAY, START_HOUR, END_HOUR, is_training=False)
        print("DAY: {}, Requests: {}".format(TEST_DAY, total_requests_served))
