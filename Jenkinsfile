elifePipeline {
    def commit
    stage 'Checkout', {
        checkout scm
        commit = elifeGitRevision()
    }
    milestone label: 'checkout'

    stage 'End2end tests run', {
        elifeSpectrum(environmentName: 'end2end', processes: 15, revision: commit)
    }
    milestone label: 'end2end-tests'

    stage 'Quick load test', {
        elifeLoad(environmentName: 'end2end', revision: commit)
    }
    milestone label: 'load-tests'

    elifeMainlineOnly {
        stage 'Update all nodes', {
            lock('spectrum') {
                builderUpdate 'elife-libraries--spectrum'
            }
        }
    }
}
