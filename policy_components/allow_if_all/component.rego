package pf.components.allow_if_all

import rego.v1

# AllowIfAll: allows when every decision it takes allows and, for each parameter some of them
# name, those that name it admit a value in common. Its parameters are, for each name, the
# values every decision naming it admits: their intersection. A parameter a decision does not
# name, it does not restrict.
#   decisions  Decision  one or more
# -> Decision about whom they are about. No policy data.
interface := {
	"output": "Decision",
	"inputs": {"decisions": {"type": "Decision"}},
	"policy_data_schema": {},
}

decisions := input.inputs.decisions

# every parameter some decision names
names contains name if {
	some d in decisions
	some name, _ in d.parameters
}

# the values one decision admits for a parameter it names
admitted(d, name) := values if {
	values := {v | some v in d.parameters[name]}
}

# the values every decision naming the parameter admits
common(name) := values if {
	values := intersection({admitted(d, name) | some d in decisions; name in object.keys(d.parameters)})
}

parameters[name] := sort(common(name)) if some name in names

default allow := false

allow if {
	every d in decisions {
		d.allow == true
	}
	every name in names {
		count(common(name)) > 0
	}
}

output := {"allow": allow, "parameters": parameters}
