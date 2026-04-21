# JWT keys

This folder holds the RSA keypair used to sign (auth-service) and verify
(everything else) JWT tokens. Keys are **never** committed.

To generate a fresh keypair:

```bash
./scripts/generate_keys.sh
```

This creates `jwt_private.pem` (chmod 600) and `jwt_public.pem` (chmod 644).
The folder is mounted read-only into the relevant containers in
`docker-compose.yml`.
