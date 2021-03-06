PINBOT = {"COMMAND_HELP":
              [["Command", "Params", "Description", "Note"],
               ["help", "", "This command!", "My brother! He's dying! Get help!"],
               ["help_note", "", "Shows notes instead of description", ""],
               ["setup", "", "Help with setting up & Common problems", ""],

               ["setmax", "[#|max pins]", "Sets the max # of pins before embedding", "Short for ,,config set PIN_THRESHOLD [#]"],
               ["map", "[#from-channel] [#to-channel]", "Saves pins from [#from-channel] to [#to-channel]", "many-to-one"],
               ["unmap", "[#from]", "Stops saving pins from [from-channel]", "probably avoid spaces"],
               ["whitelist", "[@|role/member]", "Allow/Forbid role/member using commands", "Try a mention?"],
               ["setprefix", "[prefix]", "Sets prefix to [prefix]", ""],
               ["", "", "", ""],
               ["config set", "[name] [val]", "Sets config [name] to literal_eval([val])", "With great power..."],
               ["config unset", "[name]", "Restores config [name] to default", "...comes great responsibility"],
               ["config reset", "", "Restores all config to default", "In case of emergency, break glass"],
               ["config print", "", "Prints current config", "Secret settings pending documentation..."],
               ["", "", "", ""],
               ["pinall", "", "Manually embeds current channel until pins < max", "Takes some time"],

               ]}
