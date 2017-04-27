elifePipeline {
    def commit
    stage 'Checkout', {
        checkout scm
        commit = elifeGitRevision()
    }

    stage 'End2end tests run', {
        elifeSpectrum(environmentName: 'end2end', processes: 15, revision: commit)
    }

    stage 'Quick load test', {
        elifeLoad(environmentName: 'end2end', revision: commit)
    }
}
