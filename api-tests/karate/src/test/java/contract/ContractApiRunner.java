package contract;

import com.intuit.karate.junit5.Karate;

class ContractApiRunner {

    @Karate.Test
    Karate testApiContracts() {
        return Karate.run("api-contract").relativeTo(getClass());
    }
}

