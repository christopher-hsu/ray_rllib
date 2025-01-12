### Bayesian Q-learning with Assumed Density Filtering (https://arxiv.org/abs/1712.03333)
======================================

Author: Heejin Chloe Jeong (heejinj@seas.upenn.edu)

Affiliation: University of Pennsylvania, Philadelphia, PA


### RLlib: Scalable Reinforcement Learning
======================================

RLlib is an open-source library for reinforcement learning that offers both high scalability and a unified API for a variety of applications.

For an overview of RLlib, see the [documentation](http://ray.readthedocs.io/en/latest/rllib.html).

If you've found RLlib useful for your research, you can cite the [paper](https://arxiv.org/abs/1712.09381) as follows:

```
@inproceedings{liang2018rllib,
    Author = {Eric Liang and
              Richard Liaw and
              Robert Nishihara and
              Philipp Moritz and
              Roy Fox and
              Ken Goldberg and
              Joseph E. Gonzalez and
              Michael I. Jordan and
              Ion Stoica},
    Title = {{RLlib}: Abstractions for Distributed Reinforcement Learning},
    Booktitle = {International Conference on Machine Learning ({ICML})},
    Year = {2018}
}
```
### To start image and container
```
./build-docker.sh
```

### To use terminal
```
docker exec -it RLlib bash
```

Opens shell and drops you into the rllib directory.

### IMPORTANT steps
```
cd RL && source setup
cd gym && pip install -e '.[atari]'
cd ../
```

### To close container
```
docker ps -a
docker container stop RLlib
docker container rm RLlib
```
