# zuora-aqua-client-cli [![Build Status](https://travis-ci.com/molnarjani/zuora-aqua-client-cli.svg?branch=master)](https://travis-ci.com/molnarjani/zuora-aqua-client-cli)

Run ZOQL queries through AQuA from the command line

# Usage

#### Zacc
```
Usage: zacc [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  describe  List available fields of Zuora resource
  query     Run ZOQL Query                        Show this message and exit.
```

#### Query
```
Usage: zacc query [OPTIONS]

  Run ZOQL Query

Options:
  -c, --config-filename PATH      Config file containing Zuora ouath
                                  credentials  [default: zuora_oauth.ini]
  -z, --zoql PATH                 ZOQL file to be executed  [default:
                                  input.zoql]
  -o, --output PATH               Where to write the output to, default is
                                  STDOUT
  -e, --environment [prod|preprod|local]
                                  Zuora environment to execute on  [default:
                                  local]
  -m, --max-retries INTEGER       Maximum retries for query
  --help                          Show this message and exit.
```

#### Describe [WIP]
```
Usage: zacc describe [OPTIONS] RESOURCE

  List available fields of Zuora resource

Options:
  --help  Show this message and exit.
```

# Useful stuff
Has a lot of graphs on Resource relationships:
https://community.zuora.com/t5/Engineering-Blog/AQUA-An-Introduction-to-Join-Processing/ba-p/13262
