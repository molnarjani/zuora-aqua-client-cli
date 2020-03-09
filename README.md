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

If option is not provided, will be read from `~/.zacc.ini`

#### Example config
```
[zacc]
# When environement option is ommited the default environment will be used
default_environment = preprod

[prod]
# Use production Zuora endpoints, defaults to `false`
production = true                                            
client_id = <oauth_client_id>
client_secret = <oauth_client_secret>

# Optional partner and project fields can be configured per environment, see more on what these do:
# https://knowledgecenter.zuora.com/Central_Platform/API/AB_Aggregate_Query_API/B_Submit_Query
# partner = partner
# project = myproject

[mysandbox]
client_id = <oauth_client_id>
client_secret = <oauth_client_secret>
```

# Usage

#### Cheatsheet
```
# List fiels for resource
$ zacc describe Account
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
$ zacc bearer
Bearer aaaaaaaaaaaaaaaaaaaaaaaaaaa

# Execute an AQuA job
$ zacc query "select Account.Name from Account where Account.CreatedDate > '2019-01-10'"
Account.Name
John Doe
Jane Doe

# Save results to CSV file instead of printing it
$ zacc query ~/query_names.zoql -o account_names.csv

# Execute an AQuA job from a ZOQL query file
$ zacc query ~/query_names.zoql
Account.Name
John Doe
Jane Doe

# Use different configurations than default
$ zacc -c ~/.myotherzaccconfig.ini -e notdefualtenv query ~/query_names.zoql
```

## Commands

#### zacc
```
Usage: zacc [OPTIONS] COMMAND [ARGS]...

  Sets up an API client, passes to commands in context

Options:
  -c, --config-filename PATH  Config file containing Zuora ouath credentials
                              [default: /Users/janosmolnar/.zacc.ini]

  -e, --environment TEXT      Zuora environment to execute on
  --project TEXT              Project name
  --partner TEXT              Partner name
  -m, --max-retries FLOAT     Maximum retries for query
  --help                      Show this message and exit.

Commands:
  bearer    Prints bearer than exits
  describe  List available fields of Zuora resource
  query     Run ZOQL Query
```

#### zacc query
```
Usage: zacc query [OPTIONS]

  Run ZOQL Query

Options:
  -o, --output PATH        Where to write the output to, default is STDOUT
  --help                   Show this message and exit.
```

#### zacc describe
```                                                                                                     
Usage: zacc describe [OPTIONS] RESOURCE

  List available fields of Zuora resource

Options:
  --help  Show this message and exit.
```

#### zacc bearer
```
Usage: zacc bearer [OPTIONS]

  Prints bearer than exits

Options:
  --help  Show this message and exit.
```

# Useful stuff
Has a lot of graphs on Resource relationships:
https://knowledgecenter.zuora.com/BB_Introducing_Z_Business/D_Zuora_Business_Objects_Relationship
https://community.zuora.com/t5/Engineering-Blog/AQUA-An-Introduction-to-Join-Processing/ba-p/13262
