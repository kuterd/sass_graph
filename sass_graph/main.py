import sass_cfg

functions = sass_cfg.generate_cfgs(sass_cfg.disassemble("elf.o"))
func = next(iter(functions.values()))
func.dump("result.html")
