Feature: Cart add API

  Background:
    * url karate.get('baseUrl')
    # authenticate once and set auth header for subsequent requests
    * path '/auth/login'
    * request { email: 'test@example.com', password: 'password123' }
    * method post
    * status 200
    * def token = response.accessToken
    # ensure a clean cart before each scenario
    * path '/cart/clear'
    * header Authorization = 'Bearer ' + token
    * method post
    * status 200

  Scenario: Add valid item to cart
    Given path '/cart/add'
    And header Authorization = 'Bearer ' + token
    And request { productId: 1, quantity: 2 }
    When method post
    Then status 201
    And match response ==
      """
      {
        message: 'Item added to cart',
        cart: [
          { productId: 1, quantity: 2 }
        ]
      }
      """

  Scenario: Add with invalid productId
    Given path '/cart/add'
    And header Authorization = 'Bearer ' + token
    And request { productId: 999, quantity: 1 }
    When method post
    Then status 400
    And match response == { error: 'Invalid productId' }

  Scenario: Add with invalid quantity
    Given path '/cart/add'
    And header Authorization = 'Bearer ' + token
    And request { productId: 1, quantity: 0 }
    When method post
    Then status 400
    And match response == { error: 'Invalid quantity' }

