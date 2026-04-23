from omegaconf import OmegaConf


cfg = OmegaConf.create(
    {
        "name": "OmegaConf",
        "release": "???",
        "greeting": "Hello ${name}",
        "subprojects": {
            "omegaconf-pydevd": {
                "version": "???",
                "status": "debugger plugin",
            }
        },
        "project": "${subprojects.omegaconf-pydevd}",
    }
)

# Put a breakpoint on the next line and inspect:
# - cfg
# - cfg.greeting
# - cfg.subprojects
# - cfg.project
print(cfg)
