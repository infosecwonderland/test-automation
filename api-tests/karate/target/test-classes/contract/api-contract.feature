Feature: API contract validation - auth only

  Background:
    * url karate.get('baseUrl')
    * configure logPrettyRequest = true
    * configure logPrettyResponse = true
    # login once and attach token to all requests
    * def email = karate.get('auth.email', karate.properties['auth.email'])
    * def password = karate.get('auth.password', karate.properties['auth.password'])
    Given path '/auth/login'
    And request { email: '#(email)', password: '#(password)' }
    When method post
    Then status 200
    * def token = response.accessToken
    * configure headers = { Authorization: '#("Bearer " + token)' }

  # Auth contract: login response must contain a JWT accessToken and tokenType.
  # Username and password come from config or system properties so they are not hardcoded.
  Scenario: Contract - POST /auth/login
    * def email = karate.get('auth.email', karate.properties['auth.email'])
    * def password = karate.get('auth.password', karate.properties['auth.password'])
    Given path '/auth/login'
    And request { email: '#(email)', password: '#(password)' }
    When method post
    Then status 200
    * def loginSchema =
      """
      {
        accessToken: '#regex ^[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+$',
        tokenType: '#string'
      }
      """
    And match response == loginSchema

  # Contract: /auth/login should only accept JSON payloads
  Scenario: Contract - /auth/login rejects non-JSON payload
    * def email = karate.get('auth.email', karate.properties['auth.email'])
    * def password = karate.get('auth.password', karate.properties['auth.password'])
    Given path '/auth/login'
    And header Content-Type = 'text/plain'
    And request 'email=' + email + '&password=' + password
    When method post
    Then assert responseStatus >= 400

  # Contract: /auth/login should not accept non-POST methods
  Scenario: Contract - /auth/login rejects non-POST method
    Given path '/auth/login'
    When method get
    Then assert responseStatus >= 400

  # Products contract: GET /products
  Scenario: Contract - GET /products
    Given path '/products'
    When method get
    Then status 200
    And match response == '#[]'          
    * def productSchema =
      """
      {
        id: '#number',
        name: '#string',
        price: '#number'
      }
      """
    And match each response == productSchema
    # additional business rules: id positive, price positive
    And match each response[*].id == '#? _ > 0'
    And match each response[*].price == '#? _ > 0'

  # Cart contract: POST /cart/add - happy path schema and constraints
  Scenario: Contract - POST /cart/add
    Given path '/cart/clear'
    When method post
    Then status 200

    Given path '/cart/add'
    And request { productId: 1, quantity: 2 }
    When method post
    Then status 201
    And match response.message == '#string'
    And match response.cart == '#[]'
    * def cartItemSchema =
      """
      {
        productId: '#number',
        quantity: '#number'
      }
      """
    And match each response.cart == cartItemSchema
    And match each response.cart[*].productId == '#? _ > 0'
    And match each response.cart[*].quantity == '#? _ > 0'

  # Cart contract: POST /cart/add - error schema for invalid input
  Scenario: Contract - POST /cart/add invalid productId
    Given path '/cart/add'
    And request { productId: 99999, quantity: 1 }
    When method post
    Then status 400
    And match response ==
      """
      {
        error: '#string'
      }
      """

  # Cart contract: /cart/add should not accept non-POST methods
  Scenario: Contract - /cart/add rejects non-POST method
    Given path '/cart/add'
    When method get
    Then assert responseStatus >= 400

    Given path '/cart/add'
    When method put
    Then assert responseStatus >= 400

    Given path '/cart/add'
    When method delete
    Then assert responseStatus >= 400

  # Cart contract: /cart/add should only accept JSON payloads
  Scenario: Contract - /cart/add rejects non-JSON payload
    Given path '/cart/add'
    And header Content-Type = 'text/plain'
    And request 'productId=1&quantity=2'
    When method post
    Then assert responseStatus >= 400

  # Order contract: POST /order/create - happy path schema and constraints
  Scenario: Contract - POST /order/create
    # arrange: ensure cart has at least one item
    Given path '/cart/clear'
    When method post
    Then status 200

    Given path '/cart/add'
    And request { productId: 1, quantity: 2 }
    When method post
    Then status 201

    # act: create order
    Given path '/order/create'
    And request {}               # explicit JSON body
    When method post
    Then status 201
    * def orderSchema =
      """
      {
        message: '#string',
        orderId: '#string',
        total: '#number'
      }
      """
    And match response == orderSchema
    And match response.total == '#? _ > 0'

  # Order contract: POST /order/create - error schema when cart is empty
  Scenario: Contract - POST /order/create empty cart
    Given path '/cart/clear'
    When method post
    Then status 200

    Given path '/order/create'
    And request {}
    When method post
    Then status 400
    And match response ==
      """
      {
        error: '#string'
      }
      """

  # Order contract: /order/create should not accept non-POST methods
  Scenario: Contract - /order/create rejects non-POST method
    Given path '/order/create'
    When method get
    Then assert responseStatus >= 400

    Given path '/order/create'
    When method put
    Then assert responseStatus >= 400

    Given path '/order/create'
    When method delete
    Then assert responseStatus >= 400

  # Order contract: /order/create should only accept JSON payloads
  Scenario: Contract - /order/create rejects non-JSON payload
    Given path '/order/create'
    And header Content-Type = 'text/plain'
    And request 'create=order'
    When method post
    Then assert responseStatus >= 400

  # Payment contract: POST /payment/charge - happy path schema and constraints
  Scenario: Contract - POST /payment/charge
    # arrange: create a valid order first
    Given path '/cart/clear'
    When method post
    Then status 200

    Given path '/cart/add'
    And request { productId: 1, quantity: 1 }
    When method post
    Then status 201

    Given path '/order/create'
    And request {}
    When method post
    Then status 201
    * def orderId = response.orderId

    # act: charge payment
    Given path '/payment/charge'
    And request { orderId: '#(orderId)', cardNumber: '4111111111111111' }
    When method post
    Then status 200
    * def paymentSchema =
      """
      {
        message: '#string',
        orderId: '#string',
        status: '#string'
      }
      """
    And match response == paymentSchema
    And match response.orderId == orderId
    And match response.status == '#regex ^PAID|SUCCESS$'

  # Payment contract: POST /payment/charge - error when order does not exist
  Scenario: Contract - POST /payment/charge non-existent order
    Given path '/payment/charge'
    And request { orderId: 'non-existent-order', cardNumber: '4111' }
    When method post
    Then status 404
    And match response ==
      """
      {
        error: '#string'
      }
      """

  # Payment contract: POST /payment/charge - error when card details invalid
  Scenario: Contract - POST /payment/charge invalid card
    # arrange: create a valid order
    Given path '/cart/clear'
    When method post
    Then status 200

    Given path '/cart/add'
    And request { productId: 1, quantity: 1 }
    When method post
    Then status 201

    Given path '/order/create'
    And request {}
    When method post
    Then status 201
    * def orderId = response.orderId

    # act with bad card - expect 400 from request validation / handler
    Given path '/payment/charge'
    And request { orderId: '#(orderId)', cardNumber: '123' }
    When method post
    Then status 400

  # Payment contract: /payment/charge should not accept non-POST methods
  Scenario: Contract - /payment/charge rejects non-POST method
    Given path '/payment/charge'
    When method get
    Then assert responseStatus >= 400

    Given path '/payment/charge'
    When method put
    Then assert responseStatus >= 400

    Given path '/payment/charge'
    When method delete
    Then assert responseStatus >= 400

  # Payment contract: /payment/charge should only accept JSON payloads
  Scenario: Contract - /payment/charge rejects non-JSON payload
    Given path '/payment/charge'
    And header Content-Type = 'text/plain'
    And request 'orderId=123&cardNumber=4111'
    When method post
    Then assert responseStatus >= 400
  
  # /cart/add should not accept non-POST methods
  Scenario: Contract - /cart/add rejects non-POST method
    Given path '/cart/add'
    When method get
    Then assert responseStatus >= 400

    Given path '/cart/add'
    When method put
    Then assert responseStatus >= 400

    Given path '/cart/add'
    When method delete
    Then assert responseStatus >= 400

  # /cart/add should only accept JSON payloads
    Scenario: Contract - /cart/add rejects non-JSON payload
    Given path '/cart/add'
    And header Content-Type = 'text/plain'
    And request 'productId=1&quantity=2'
    When method post
    Then assert responseStatus >= 400

  