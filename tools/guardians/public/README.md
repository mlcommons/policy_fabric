# public guardian

An asset server with no guardian behind it: it hands the file it was started on
to any caller, unauthenticated. It exists so a demo can show an open asset next
to a policy-gated one.

Only the health endpoint is shared with the real guardians; there is no
capability processing, no policy contract binding, and no PDO dependency.

| Method | Path         | Returns                                  |
|--------|--------------|------------------------------------------|
| GET    | `/info`      | `{service, guardian_type, data_length}`   |
| GET    | `/`, `/data` | the data file, as plain text              |

```bash
./run.sh --interface 127.0.0.1 --port 7900 --data-path /tmp/asset_data.txt
```

Stop it with `kill` on the process; there is no container to remove.
