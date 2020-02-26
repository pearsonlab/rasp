# improv
Adaptive Platform for Real-time Analysis of Neural Circuits


## Under active development! Please check back soon for installation instructions.

improv is a streaming software platform designed to enable adaptive experiments. By analyzing data, such as 2-photon calcium images, as it comes in, we can obtain information about the current brain state in real time and use it to adaptively modify the experiment. 

![](https://web.duke.edu/mind/level2/faculty/pearson/assets/videos/zebrafish/improvGif.gif)

This video shows raw 2-photon calcium imaging data in zebrafish, with cells detected in real time by CaImAn, and directional tuning curves (shown as colored neurons) and functional connectivity (lines) estimated online, during a live experiment.
We can provide up-to-the-moment estimates of the functional connectivity by fitting linear-nonlinear-Poisson models online, as each new piece of data is acquired. Simple visualizations offer real-time insights, allowing for adaptive experiments that change in response to the current state of the brain.


### How improv works

improv's design is based on a steamlined version of the actor model for concurrent computation. Each component of the system (experimental pipeline) is considered an 'actor' and has a unique role. They interact via message passing, without the need for a central broker. Actors are implemented as user-defined classes that inherit from improv's Actor class, which supplies all queues for message passing and orchestrates process execution and error handling. Messages between actors are composed of keys that correspond to items in a shared, in-memory data store. This both minimizes communication overhead and data copying between processes. 

<img src="https://web.duke.edu/mind/level2/faculty/pearson/assets/images/zebrafish/actor_model.png" width=70%>

### Contact
To get in touch, feel free to email us at anne.draelos@duke.edu or reach out on Twitter <a href="http://twitter.com/annedraelos" target="_blank">@annedraelos</a>. 
