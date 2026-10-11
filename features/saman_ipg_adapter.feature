@unit @ipg @saman
Feature: Saman Shaparak payment gateway adapter

  Scenario Outline: Initiate a payment and receive a token
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "token" endpoint answers 200 with JSON:
      """
      {
        "status": 1,
        "token": "tok-abc-123"
      }
      """
    When I initiate a Saman payment of 75000 for reservation "RES-1" redirecting to "https://shop.example.com/return"
    Then the Saman initiation response has status 1 and token "tok-abc-123"
    And the Saman initiation response has no error
    And the Saman "token" endpoint received JSON with:
      | action | TerminalId | Amount | ResNum | RedirectUrl                     | TokenExpiryInMin |
      | token  | 13579      | 75000  | RES-1  | https://shop.example.com/return | 20               |
    And the Saman "token" endpoint received no field "CellNumber"
    And the Saman "token" endpoint received no field "Wage"
    And the Saman "token" endpoint received no field "HashedCardNumber"

    Examples:
      | kind         |
      | sync         |
      | async        |
      | sync Neo-PG  |
      | async Neo-PG |

  Scenario Outline: Optional payment fields are sent when provided
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "token" endpoint answers 200 with JSON:
      """
      {
        "status": 1,
        "token": "tok-abc-123"
      }
      """
    When I initiate a Saman payment of 75000 redirecting to "https://shop.example.com/return" with options:
      | ResNum | CellNumber  | Wage | TokenExpiryInMin | HashedCardNumber |
      | RES-2  | 09123456789 | 500  | 30               | abcdef           |
    Then the Saman "token" endpoint received JSON with:
      | CellNumber  | Wage | TokenExpiryInMin | HashedCardNumber |
      | 09123456789 | 500  | 30               | abcdef           |

    Examples:
      | kind         |
      | sync         |
      | async        |
      | sync Neo-PG  |
      | async Neo-PG |

  Scenario Outline: Neo-PG adapter exposes the dynamic payment page URL
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "token" endpoint answers 200 with JSON:
      """
      {
        "status": 1,
        "token": "tok-abc-123"
      }
      """
    And the Saman "token" endpoint sends header "X-IPG-Url" with value "https://pay.example.com/page/42"
    When I initiate a Saman payment of 75000 for reservation "RES-1" redirecting to "https://shop.example.com/return"
    Then the Saman initiation response has IPG URL "https://pay.example.com/page/42"

    Examples:
      | kind         |
      | sync Neo-PG  |
      | async Neo-PG |

  Scenario Outline: Classic adapter ignores the dynamic payment page URL header
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "token" endpoint answers 200 with JSON:
      """
      {
        "status": 1,
        "token": "tok-abc-123"
      }
      """
    And the Saman "token" endpoint sends header "X-IPG-Url" with value "https://pay.example.com/page/42"
    When I initiate a Saman payment of 75000 for reservation "RES-1" redirecting to "https://shop.example.com/return"
    Then the Saman initiation response has no IPG URL

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Gateway reports an initiation failure
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "token" endpoint answers 200 with JSON:
      """
      {
        "status": -1,
        "errorCode": "5",
        "errorDesc": "Duplicate reservation number"
      }
      """
    When I initiate a Saman payment of 75000 for reservation "RES-1" redirecting to "https://shop.example.com/return"
    Then the Saman initiation response has status -1 and no token
    And the Saman initiation response has error code "5" and description "Duplicate reservation number"

    Examples:
      | kind         |
      | sync         |
      | async        |
      | sync Neo-PG  |
      | async Neo-PG |

  Scenario Outline: Inconsistent initiation replies are reported as internal error
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "token" endpoint answers 200 with JSON:
      """
      <body>
      """
    When I initiate a Saman payment of 75000 for reservation "RES-1" redirecting to "https://shop.example.com/return"
    Then the Saman call fails with "InternalError"

    Examples:
      | kind         | body             |
      | sync         | {"status": 1}    |
      | async        | {"status": 1}    |
      | sync         | {"status": -1}   |
      | async        | {"status": -1}   |
      | sync         | {"token": "tok"} |
      | async        | {"token": "tok"} |
      | sync Neo-PG  | {"status": 1}    |
      | async Neo-PG | {"status": -1}   |

  Scenario Outline: Gateway HTTP error or unreadable body during initiation is reported as internal error
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "token" endpoint answers <http_status> with raw body "<body>"
    When I initiate a Saman payment of 75000 for reservation "RES-1" redirecting to "https://shop.example.com/return"
    Then the Saman call fails with "InternalError"

    Examples:
      | kind         | http_status | body     |
      | sync         | 500         | oops     |
      | async        | 500         | oops     |
      | sync         | 200         | not json |
      | async        | 200         | not json |
      | sync Neo-PG  | 503         | down     |
      | async Neo-PG | 200         | not json |

  Scenario Outline: Unreachable gateway during initiation is reported as unavailable
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "token" endpoint fails with a <failure>
    When I initiate a Saman payment of 75000 for reservation "RES-1" redirecting to "https://shop.example.com/return"
    Then the Saman call fails with "UnavailableError"
    And the Saman failure carries resource type "<resource>"

    Examples:
      | kind         | failure          | resource                   |
      | sync         | connection error | Saman Token Service        |
      | async        | connection error | Saman Token Service        |
      | sync         | timeout          | Saman Token Service        |
      | async        | timeout          | Saman Token Service        |
      | sync Neo-PG  | connection error | Saman Neo-PG Token Service |
      | async Neo-PG | timeout          | Saman Neo-PG Token Service |

  Scenario Outline: Verify a successful payment
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "verify" endpoint answers 200 with JSON:
      """
      {
        "Success": true,
        "ResultCode": 0,
        "ResultDescription": "OK",
        "TransactionDetail": {
          "RRN": "112233",
          "RefNum": "REF-9",
          "MaskedPan": "603799******1234",
          "HashedPan": "hash-1",
          "OrginalAmount": 75000,
          "AffectiveAmount": 74500,
          "StraceNo": "000123"
        }
      }
      """
    When I verify Saman reference "REF-9"
    Then the Saman verification succeeded with result code 0 and description "OK"
    And the Saman verification detail has rrn "112233" and reference "REF-9"
    And the Saman verification detail has masked pan "603799******1234" and hashed pan "hash-1"
    And the Saman verification detail has original amount 75000, affective amount 74500 and trace "000123"
    And the Saman "verify" endpoint received JSON with:
      | RefNum | TerminalNumber |
      | REF-9  | 13579          |

    Examples:
      | kind         |
      | sync         |
      | async        |
      | sync Neo-PG  |
      | async Neo-PG |

  Scenario Outline: Verify reports a failed transaction
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "verify" endpoint answers 200 with JSON:
      """
      {
        "Success": false,
        "ResultCode": -2,
        "ResultDescription": "Transaction not found",
        "TransactionDetail": null
      }
      """
    When I verify Saman reference "REF-404"
    Then the Saman verification failed with result code -2 and description "Transaction not found"
    And the Saman verification detail is empty

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Verify with an empty reply falls back to unknown result
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "verify" endpoint answers 200 with JSON:
      """
      {}
      """
    When I verify Saman reference "REF-1"
    Then the Saman verification failed with result code -1 and description "Unknown"
    And the Saman verification detail is empty

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Verify failures are mapped to ArchiPy errors
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "verify" endpoint <behaviour>
    When I verify Saman reference "REF-1"
    Then the Saman call fails with "<error>"

    Examples:
      | kind  | behaviour                           | error            |
      | sync  | fails with a connection error       | UnavailableError |
      | async | fails with a connection error       | UnavailableError |
      | sync  | fails with a timeout                | UnavailableError |
      | async | fails with a timeout                | UnavailableError |
      | sync  | answers 500 with raw body "bad"     | InternalError    |
      | async | answers 500 with raw body "bad"     | InternalError    |
      | sync  | answers 200 with raw body "garbage" | InternalError    |
      | async | answers 200 with raw body "garbage" | InternalError    |

  Scenario Outline: Verify outage carries the verify service resource type
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "verify" endpoint fails with a connection error
    When I verify Saman reference "REF-1"
    Then the Saman failure carries resource type "Saman Verify Service"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Verify with a non-numeric terminal id is reported as internal error
    Given a <kind> Saman adapter with terminal "TERM-X"
    When I verify Saman reference "REF-1"
    Then the Saman call fails with "InternalError"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Reverse a payment
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "reverse" endpoint answers 200 with JSON:
      """
      {
        "Success": true,
        "ResultCode": 0,
        "ResultDescription": "Reversed"
      }
      """
    When I reverse Saman reference "REF-9"
    Then the Saman reversal succeeded with result code 0 and description "Reversed"
    And the Saman "reverse" endpoint received JSON with:
      | RefNum | TerminalNumber |
      | REF-9  | 13579          |

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Reverse reports a gateway refusal
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "reverse" endpoint answers 200 with JSON:
      """
      {
        "Success": false,
        "ResultCode": -6,
        "ResultDescription": "Already reversed"
      }
      """
    When I reverse Saman reference "REF-9"
    Then the Saman reversal failed with result code -6 and description "Already reversed"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Reverse with an empty reply falls back to unknown result
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "reverse" endpoint answers 200 with JSON:
      """
      {}
      """
    When I reverse Saman reference "REF-9"
    Then the Saman reversal failed with result code -1 and description "Unknown"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Reverse failures are mapped to ArchiPy errors
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "reverse" endpoint <behaviour>
    When I reverse Saman reference "REF-9"
    Then the Saman call fails with "<error>"
    And the Saman failure carries resource type "<resource>"

    Examples:
      | kind  | behaviour                     | error            | resource              |
      | sync  | fails with a connection error | UnavailableError | Saman Reverse Service |
      | async | fails with a connection error | UnavailableError | Saman Reverse Service |

  Scenario Outline: Reverse HTTP error is reported as internal error
    Given a <kind> Saman adapter with terminal "13579"
    And the Saman "reverse" endpoint answers 502 with raw body "bad gateway"
    When I reverse Saman reference "REF-9"
    Then the Saman call fails with "InternalError"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Adapter refuses to start without a terminal id
    When I create a <kind> Saman adapter with no terminal
    Then the Saman call fails with "InvalidArgumentError"

    Examples:
      | kind         |
      | sync         |
      | async        |
      | sync Neo-PG  |
      | async Neo-PG |

  Scenario Outline: Adapter takes its terminal id from global config when no config is given
    Given the global Saman terminal id is "24680"
    And the Saman "reverse" endpoint answers 200 with JSON:
      """
      {
        "Success": true,
        "ResultCode": 0,
        "ResultDescription": "Reversed"
      }
      """
    When I create a <kind> Saman adapter from global config
    And I reverse Saman reference "REF-1"
    Then the Saman "reverse" endpoint received JSON with:
      | RefNum | TerminalNumber |
      | REF-1  | 24680          |

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Proxy configuration picks the first available scheme
    Given a <kind> Saman adapter using proxies "<proxies>"
    Then the Saman HTTP client uses proxy "<expected>"

    Examples:
      | kind  | proxies                                    | expected           |
      | sync  | https=http://a.test:1,http=http://b.test:2 | http://a.test:1    |
      | sync  | http=http://b.test:2                       | http://b.test:2    |
      | sync  | socks5=socks5://c.test:3                   | socks5://c.test:3  |
      | sync  | none                                       | none               |
      | async | https=http://a.test:1,http=http://b.test:2 | http://a.test:1    |
      | async | http=http://b.test:2                       | http://b.test:2    |
      | async | socks5h=socks5h://d.test:4                 | socks5h://d.test:4 |
      | async | none                                       | none               |

  Scenario Outline: Invalid request data is rejected before reaching the gateway
    When I build a Saman payment request with <field> <value>
    Then the Saman request is rejected as invalid

    Examples:
      | field        | value     |
      | amount       | 0         |
      | amount       | -10       |
      | token_expiry | 5         |
      | token_expiry | 3601      |
      | redirect_url | not-a-url |
      | res_num      | none      |
