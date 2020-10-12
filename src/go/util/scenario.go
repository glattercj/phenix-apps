package util

import (
	"phenix/types"
	v1 "phenix/types/version/v1"
)

func ExtractExperimentApp(scenario *v1.ScenarioSpec, name string) *v1.ExperimentApp {
	if scenario.Apps == nil {
		return nil
	}

	for _, app := range scenario.Apps.Experiment {
		if app.Name == name {
			return &app
		}
	}

	return nil
}

func ExtractHostApp(scenario *v1.ScenarioSpec, name string) *v1.HostApp {
	if scenario.Apps == nil {
		return nil
	}

	for _, app := range scenario.Apps.Host {
		if app.Name == name {
			return &app
		}
	}

	return nil
}

func ExtractNode(topo *v1.TopologySpec, hostname string) *v1.Node {
	for _, node := range topo.Nodes {
		if node.General.Hostname == hostname {
			return node
		}
	}

	return nil
}

func ExtractNodesTopologyType(topo *v1.TopologySpec, types ...string) []*v1.Node {
	var nodes []*v1.Node

	for _, node := range topo.Nodes {
		for _, typ := range types {
			if node.Type == typ {
				nodes = append(nodes, node)
				break
			}
		}
	}

	return nodes
}

func ExtractNodesType(scenario *v1.ScenarioSpec, name string, types ...string) []*v1.Host {
	app := ExtractHostApp(scenario, name)

	var hosts []*v1.Host

	for _, host := range app.Hosts {
		if t, ok := host.Metadata["type"].(string); ok {
			if StringSliceContains(types, t) {
				hosts = append(hosts, &host)
			}
		}
	}

	return hosts
}

func ExtractNodesLabel(scenario *v1.ScenarioSpec, name string, labels ...string) []*v1.Host {
	app := ExtractHostApp(scenario, name)

	var hosts []*v1.Host

	for _, host := range app.Hosts {
		if l, ok := host.Metadata["labels"].([]string); ok {
			if StringSliceContains(labels, l...) {
				hosts = append(hosts, &host)
			}
		}
	}

	return hosts
}

func ExtractAssetDir(scenario *v1.ScenarioSpec, name string) string {
	if scenario.Apps == nil {
		return ""
	}

	for _, app := range scenario.Apps.Experiment {
		if app.Name == name {
			return app.AssetDir
		}
	}

	for _, app := range scenario.Apps.Host {
		if app.Name == name {
			return app.AssetDir
		}
	}

	return ""
}

func IsFullyScheduled(exp types.Experiment) bool {
	schedules := exp.Spec.Schedules

	for _, node := range exp.Spec.Topology.Nodes {
		if _, ok := schedules[node.General.Hostname]; !ok {
			return false
		}
	}

	return true
}

func GetAnnotation(exp types.Experiment, key string) string {
	if exp.Metadata.Annotations == nil {
		return ""
	}

	return exp.Metadata.Annotations[key]
}
