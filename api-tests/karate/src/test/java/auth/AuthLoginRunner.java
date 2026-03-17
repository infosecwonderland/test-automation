package auth;

import com.intuit.karate.junit5.Karate;

class AuthLoginRunner {

    @Karate.Test
    Karate testAuthLogin() {
        return Karate.run("auth-login").relativeTo(getClass());
    }
}

