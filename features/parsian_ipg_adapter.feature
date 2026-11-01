@unit @ipg @parsian
Feature: Parsian Shaparak payment gateway adapter

  Scenario Outline: Initiate a payment and receive a token
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway answers "SalePaymentRequest" with:
      | Token  | Status | Message |
      | 987654 | 0      | Success |
    When I initiate a Parsian payment of 50000 for order 1001 with callback "https://shop.example.com/back"
    Then the Parsian initiation response has token 987654 and status 0
    And the Parsian initiation response has message "Success"
    And the Parsian gateway received "SalePaymentRequest" on the "sale" service with:
      | LoginAccount | Amount | OrderId | CallBackUrl                   |
      | merchant-1   | 50000  | 1001    | https://shop.example.com/back |

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Gateway rejects a payment initiation with an error status
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway answers "SalePaymentRequest" with:
      | Token | Status | Message           |
      |       | -112   | Order id is taken |
    When I initiate a Parsian payment of 50000 for order 1001 with callback "https://shop.example.com/back"
    Then the Parsian initiation response has no token and status -112
    And the Parsian initiation response has message "Order id is taken"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: SOAP fault during initiation is reported as unavailable
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway raises a SOAP fault on "SalePaymentRequest"
    When I initiate a Parsian payment of 50000 for order 1001 with callback "https://shop.example.com/back"
    Then the Parsian call fails with "UnavailableError"
    And the Parsian failure carries resource type "Parsian Shaparak Sale Service"
    And the Parsian failure was caused by a SOAP fault

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Unexpected transport failure during initiation is reported as internal error
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway fails with a connection error on "SalePaymentRequest"
    When I initiate a Parsian payment of 50000 for order 1001 with callback "https://shop.example.com/back"
    Then the Parsian call fails with "InternalError"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Malformed gateway reply during initiation is reported as internal error
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway answers "SalePaymentRequest" with:
      | Token  |
      | 987654 |
    When I initiate a Parsian payment of 50000 for order 1001 with callback "https://shop.example.com/back"
    Then the Parsian call fails with "InternalError"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Confirm a payment
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway answers "ConfirmPayment" with:
      | Status | RRN       | CardNumberMasked | Token  |
      | 0      | 123456789 | 603799******1234 | 987654 |
    When I confirm Parsian token 987654
    Then the Parsian confirmation response has status 0 and rrn 123456789
    And the Parsian confirmation response has card "603799******1234" and token 987654
    And the Parsian gateway received "ConfirmPayment" on the "confirm" service with:
      | LoginAccount | Token  |
      | merchant-1   | 987654 |

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Confirm a payment with an unknown status passes the status through
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway answers "ConfirmPayment" with:
      | Status | RRN | CardNumberMasked | Token  |
      | -138   |     |                  | 987654 |
    When I confirm Parsian token 987654
    Then the Parsian confirmation response has status -138 and no rrn

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: SOAP fault during confirmation is reported as unavailable
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway raises a SOAP fault on "ConfirmPayment"
    When I confirm Parsian token 987654
    Then the Parsian call fails with "UnavailableError"
    And the Parsian failure carries resource type "Parsian Shaparak Confirm Service"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Confirm a payment with amount and order verification
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway answers "ConfirmPaymentWithAmount" with:
      | Status | RRN       | CardNumberMasked | Token  |
      | 0      | 555000111 | 502229******9876 | 987654 |
    When I confirm Parsian token 987654 for order 1001 and amount 50000
    Then the Parsian amount confirmation response has status 0 and rrn 555000111
    And the Parsian gateway received "ConfirmPaymentWithAmount" on the "confirm" service with:
      | LoginAccount | Token  | OrderId | Amount |
      | merchant-1   | 987654 | 1001    | 50000  |

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: SOAP fault during confirmation with amount is reported as unavailable
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway raises a SOAP fault on "ConfirmPaymentWithAmount"
    When I confirm Parsian token 987654 for order 1001 and amount 50000
    Then the Parsian call fails with "UnavailableError"
    And the Parsian failure carries resource type "Parsian Shaparak Confirm Service"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Reverse a payment
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway answers "ReversalRequest" with:
      | Status | Message  | Token  |
      | 0      | Reversed | 987654 |
    When I reverse Parsian token 987654
    Then the Parsian reversal response has status 0 and message "Reversed"
    And the Parsian gateway received "ReversalRequest" on the "reversal" service with:
      | LoginAccount | Token  |
      | merchant-1   | 987654 |

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: SOAP fault during reversal is reported as unavailable
    Given a <kind> Parsian adapter with login account "merchant-1"
    And the Parsian gateway raises a SOAP fault on "ReversalRequest"
    When I reverse Parsian token 987654
    Then the Parsian call fails with "UnavailableError"
    And the Parsian failure carries resource type "Parsian Shaparak Reversal Service"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Adapter refuses to start without a login account
    When I create a <kind> Parsian adapter with no login account
    Then the Parsian call fails with "InvalidArgumentError"

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: Adapter takes its login account from global config when no config is given
    Given the global Parsian login account is "global-merchant"
    And the Parsian gateway answers "ConfirmPayment" with:
      | Status | RRN | CardNumberMasked | Token |
      | 0      | 1   | 603799******1234 | 5     |
    When I create a <kind> Parsian adapter from global config
    And I confirm Parsian token 5
    Then the Parsian gateway received "ConfirmPayment" on the "confirm" service with:
      | LoginAccount    | Token |
      | global-merchant | 5     |

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: The SOAP transport bounds operations and carries the proxy only when set
    Given a <kind> Parsian adapter using proxy "<proxy>"
    Then the Parsian SOAP transport times operations and WSDL loads out after 30 seconds and <proxy_use> the proxy

    Examples:
      | kind  | proxy                 | proxy_use |
      | sync  | http://127.0.0.1:3128 | uses      |
      | sync  | none                  | skips     |
      | async | http://127.0.0.1:3128 | uses      |
      | async | none                  | skips     |

  Scenario Outline: Invalid request data is rejected before reaching the gateway
    When I build a Parsian <request> with <field> <value>
    Then the Parsian request is rejected as invalid

    Examples:
      | request         | field    | value |
      | payment request | amount   | 0     |
      | payment request | amount   | -5    |
      | payment request | order_id | 0     |
      | confirm request | token    | 0     |
      | reverse request | token    | -1    |
      | amount confirm  | amount   | 0     |

  Scenario: Invalid callback URL is rejected before reaching the gateway
    When I build a Parsian payment request whose callback is "not a url"
    Then the Parsian request is rejected as invalid

  Scenario Outline: Debug logs never contain the login account or the full token
    Given a <kind> Parsian adapter with login account "SECRETLOGIN"
    And Parsian debug logging is captured
    And the Parsian gateway answers "SalePaymentRequest" with:
      | Token  | Status | Message |
      | 987654 | 0      | Success |
    And the Parsian gateway answers "ConfirmPayment" with:
      | Status | RRN | CardNumberMasked | Token  |
      | 0      | 1   | 603799******1234 | 987654 |
    And the Parsian gateway answers "ConfirmPaymentWithAmount" with:
      | Status | RRN | CardNumberMasked | Token  |
      | 0      | 1   | 603799******1234 | 987654 |
    And the Parsian gateway answers "ReversalRequest" with:
      | Status | Message  | Token  |
      | 0      | Reversed | 987654 |
    When I initiate a Parsian payment of 50000 for order 1001 with callback "https://shop.example.com/back"
    And I confirm Parsian token 987654
    And I confirm Parsian token 987654 for order 1001 and amount 50000
    And I reverse Parsian token 987654
    Then the Parsian debug logs contain neither "SECRETLOGIN" nor "987654" but do name order 1001

    Examples:
      | kind  |
      | sync  |
      | async |

  Scenario Outline: An unreachable WSDL makes construction fail as unavailable
    Given the Parsian WSDL download fails with a timeout
    When I create a <kind> Parsian adapter while the WSDL is unreachable
    Then the Parsian call fails with "UnavailableError"
    And the Parsian failure carries resource type "Parsian Shaparak WSDL"

    Examples:
      | kind  |
      | sync  |
      | async |
