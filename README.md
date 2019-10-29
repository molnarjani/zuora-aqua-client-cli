# zuora-aqua-client-cli [![Build Status](https://travis-ci.com/molnarjani/zuora-aqua-client-cli.svg?branch=master)](https://travis-ci.com/molnarjani/zuora-aqua-client-cli)

Run ZOQL queries through AQuA from the command line

# Usage

```
$ zacc --help

Usage: zacc [OPTIONS]

Options:
  -c, --config-filename PATH      Config file containing Zuora ouath
                                  credentials  [default: zuora_oauth.ini]
  -z, --zoql PATH                 ZOQL file to be executed  [default:
                                  input.zoql]
  -e, --environment [prod|preprod|local]
                                  Zuora environment to execute on  [default:
                                  local]
  --help                          Show this message and exit.
```
