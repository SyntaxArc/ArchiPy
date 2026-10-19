Feature: Range and search input DTOs
  As a developer
  I want request ranges validated before they reach a query
  So that inverted, oversized or stale ranges are refused

  Scenario Outline: A <kind> range is checked for order
    When a <kind> range from <from> to <to> is built
    Then the range should be <outcome>

    Examples: Range orders
      | kind     | from                | to                  | outcome  |
      | integer  | 1                   | 5                   | accepted |
      | integer  | 5                   | 5                   | accepted |
      | integer  | 6                   | 5                   | rejected |
      | decimal  | 1.5                 | 2.5                 | accepted |
      | decimal  | 2.5                 | 1.5                 | rejected |
      | date     | 2024-01-01          | 2024-01-02          | accepted |
      | date     | 2024-01-02          | 2024-01-01          | rejected |
      | datetime | 2024-01-01T10:00:00 | 2024-01-01T11:00:00 | accepted |
      | datetime | 2024-01-01T11:00:00 | 2024-01-01T10:00:00 | rejected |

  Scenario Outline: A range with only <open_end> is accepted
    When an integer range with only <open_end> is built
    Then the range should be accepted

    Examples: Open ranges
      | open_end |
      | a start  |
      | an end   |
      | no ends  |

  Scenario Outline: A decimal range reads <value> as a decimal
    When a decimal range is built from the text "<value>" up to the text "10"
    Then the range should be <outcome>

    Examples: Decimal inputs
      | value | outcome  |
      | 2.50  | accepted |
      | abc   | rejected |

  Scenario Outline: An interval range of <interval> from <hours_ago_from> to <hours_ago_to> hours ago is <outcome>
    When an interval range of <interval> from <hours_ago_from> to <hours_ago_to> hours ago is built
    Then the range should be <outcome>

    Examples: Interval limits
      | interval | hours_ago_from | hours_ago_to | outcome  |
      | HOURS    | 25             | 1            | accepted |
      | HOURS    | 800            | 1            | rejected |
      | SECONDS  | 80             | 72           | rejected |
      | MINUTES  | 4              | 1            | rejected |
      | MINUTES  | 1              | 0            | accepted |

  Scenario: A search input holds a page and a sort
    When a search input with page 2 of size 10 and no sort is built
    Then the search input should hold page 2 of size 10

  Scenario: A search input without a page or a sort is accepted
    When a search input with no page and no sort is built
    Then the search input should hold no page
