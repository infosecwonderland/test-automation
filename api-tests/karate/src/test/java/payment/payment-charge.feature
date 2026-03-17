Feature: Payment charge API

  Background:
    * url karate.get('baseUrl')
    # authenticate once and set auth header for subsequent requests
    * path '/auth/login'
    * request { email: 'test@example.com', password: 'password123' }
    * method post
    * status 200
    * def token = response.accessToken
    # ensure empty cart and no leftover state
    * path '/cart/clear'
    * header Authorization = 'Bearer ' + token
    * method post
    * status 200

  Scenario: Successful payment for existing order
    # arrange: add item to cart and create an order
    Given path '/cart/add'
    And header Authorization = 'Bearer ' + token
    And request { productId: 1, quantity: 1 }
    When method post
    Then status 201

    Given path '/order/create'
    And header Authorization = 'Bearer ' + token
    When method post
    Then status 201
    And match response.message == 'Order created'
    * def orderId = response.orderId
    * print 'Created orderId:', orderId

    # act: charge payment
    Given path '/payment/charge'
    And header Authorization = 'Bearer ' + token
    And request { orderId: '#(orderId)', cardNumber: '4242' }
    When method post
    Then status 200
    And match response ==
      """
      {
        message: 'Payment successful',
        orderId: '#(orderId)',
        status: 'PAID'
      }
      """

  Scenario: Fail when order does not exist
    Given path '/payment/charge'
    And header Authorization = 'Bearer ' + token
    And request { orderId: 'non-existent', cardNumber: '4242' }
    When method post
    Then status 404
    And match response == { error: 'Order not found' }

  Scenario: Fail when card details are invalid
    # create a valid order first
    Given path '/cart/add'
    And header Authorization = 'Bearer ' + token
    And request { productId: 1, quantity: 1 }
    When method post
    Then status 201

    Given path '/order/create'
    And header Authorization = 'Bearer ' + token
    When method post
    Then status 201
    * def orderId = response.orderId

    # invalid card number (too short)
    Given path '/payment/charge'
    And header Authorization = 'Bearer ' + token
    And request { orderId: '#(orderId)', cardNumber: '12' }
    When method post
    Then status 400

