Feature: Order create API

  Background:
    * url karate.get('baseUrl')
    # authenticate once and set auth header for subsequent requests
    * path '/auth/login'
    * request { email: 'test@example.com', password: 'password123' }
    * method post
    * status 200
    * def token = response.accessToken
    * header Authorization = 'Bearer ' + token
    # start from an empty cart for each scenario
    * path '/cart/clear'
    * method post
    * status 200

  Scenario: Create order from cart items
    # add items to cart
    Given path '/cart/add'
    And header Authorization = 'Bearer ' + token
    And request { productId: 1, quantity: 2 }
    When method post
    Then status 201

    # create order
    Given path '/order/create'
    And header Authorization = 'Bearer ' + token
    When method post
    Then status 201
    And match response.message == 'Order created'
    And match response.orderId == '#string'
    And match response.total == 2400

  Scenario: Fail to create order when cart is empty
    Given path '/order/create'
    And header Authorization = 'Bearer ' + token
    When method post
    Then status 400
    And match response == { error: 'Cart is empty' }

