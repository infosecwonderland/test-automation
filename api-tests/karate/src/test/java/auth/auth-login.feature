Feature: Auth login API

  Background:
    * url karate.get('baseUrl')
    * path '/auth/login'

  Scenario: Successful login returns 200 and token fields
    Given request { email: 'test@example.com', password: 'password123' }
    When method post
    Then status 200
    And match response ==
      """
      {
        accessToken: '#string',
        tokenType: '#string'
      }
      """

  Scenario: Invalid credentials return 401 and error message
    Given request { email: 'wrong@example.com', password: 'wrongpass123' }
    When method post
    Then status 401
    And match response ==
      """
      {
        message: 'invalid credentials'
      }
      """

