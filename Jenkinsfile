pipeline {

    agent any

    stages {

        stage('Run Health Check') {

            steps {

                bat 'python healthcheck.py'

            }

        }

    }

}