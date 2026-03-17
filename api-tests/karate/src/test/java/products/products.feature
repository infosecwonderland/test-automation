Feature: Products API

  Background:
    * url karate.get('baseUrl')
    * path '/products'

  Scenario: Get all products
    When method get
    Then status 200
    And match response ==
      """
      [
        { id: 1, name: 'Laptop', price: 1200 },
        { id: 2, name: 'Headphones', price: 200 },
        { id: 3, name: 'Phone', price: 800 }
      ]
      """

