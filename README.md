# zuora-aqua-client-cli [![Build Status](https://travis-ci.com/molnarjani/zuora-aqua-client-cli.svg?branch=master)](https://travis-ci.com/molnarjani/zuora-aqua-client-cli)

Run ZOQL queries through AQuA from the command line


# Installation

#### Mac
`pip3 install zuora-aqua-client-cli`
The executable will be installed to `/usr/local/bin/zacc`

#### Linux
`pip3 install zuora-aqua-client-cli`
The executable will be installed to `~/.local/bin/zacc`

Make sure `~/.local/bin/` is added to your `$PATH`

# Configuration
Configuration should be provided by the `-c /path/to/file` option.

#### Example config
```
[prod]
production = true
client_id = <client_id>
client_secret = <client_secret>

[sandbox]
production = false
client_id = <client_id>
client_secret = <client_secret>
```

# Usage

#### Cheatsheet
```
# List fiels for resource
$ zacc describe -c ~/.config.ini -e sandbox Account
Account
  AccountNumber - Account Number
  AdditionalEmailAddresses - Additional Email Addresses
  AllowInvoiceEdit - Allow Invoice Editing
  AutoPay - Auto Pay
  Balance - Account Balance
  ...
Related Objects
  BillToContact<Contact> - Bill To
  DefaultPaymentMethod<PaymentMethod> - Default Payment Method
  ParentAccount<Account> - Parent Account
  SoldToContact<Contact> - Sold To

# Request a bearer token, then exit
$ zacc bearer -c ~/.config.ini -e sandbox
Bearer <bearer token>

# Execute an AQuA job
$ zacc query -c ~/.config.ini -e sandbox -z "select Account.Name from Account where Account.CreatedDate > '2019-01-10'"
Account.Name
John Doe
Jane Doe

# Execute an AQuA job from a ZOQL query file
$ zacc query -c ~/.config.ini -e sandbox -z ~/query_names.zoql
Account.Name
John Doe
Jane Doe
```

#### Zacc
```
Usage: zacc [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  bearer    Prints bearer than exits
  describe  List available fields of Zuora resource
  query     Run ZOQL Query
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

#### Describe
```
Usage: zacc describe [OPTIONS] RESOURCE

  List available fields of Zuora resource

Options:
  -c, --config-filename PATH      Config file containing Zuora ouath
                                  credentials  [default: zuora_oauth.ini]
  -e, --environment [prod|preprod|local]
                                  Zuora environment to execute on  [default:
                                  local]
  --help                          Show this message and exit.
```

#### Bearer
```
Usage: zacc bearer [OPTIONS]

  Prints bearer than exits

Options:
  -c, --config-filename PATH      Config file containing Zuora ouath
                                  credentials  [default: zuora_oauth.ini]
  -e, --environment [prod|preprod|local]
                                  Zuora environment to execute on  [default:
                                  local]
  --help                          Show this message and exit.
```

# Useful stuff
Has a lot of graphs on Resource relationships:
https://community.zuora.com/t5/Engineering-Blog/AQUA-An-Introduction-to-Join-Processing/ba-p/13262
