elifePipeline {
    def commit
    stage 'Checkout', {
        checkout scm
        commit = elifeGitRevision()
    }

    stage 'End2end tests run', {
        elifeEnd2endTest(null, null, 'end2end', 15, commit)
    }
}
