# Delivery modules

One per guardian type. A delivery module declares the type the asset's policy
agent issues, `issues := "policy_decision"`, and describes that decision: its
claims name the operation the guardian runs and its parameters. Policy cards
declare and describe nothing. The webapp attaches the module for the
asset's guardian when the asset is exposed.

| Guardian | Module | Operation |
|----------|--------|-----------|
| download  | [`download/`](download/) | `do_download` with the channel key the request names |
| inference | [`inference/`](inference/) | `do_inference` with the approved script digest the request names |
