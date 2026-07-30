pipeline {
    agent any

    environment {
        AWS_DEFAULT_REGION = 'us-east-1'
    }

    stages {

        stage('Verify AWS Credentials') {
            steps {
                withCredentials([
                    [$class: 'AmazonWebServicesCredentialsBinding',
                     credentialsId: 'aws-master-account']
                ]) {
                    bat '''
                    aws sts get-caller-identity
                    '''
                }
            }
        }

        stage('Run Health Check') {
            steps {
                withCredentials([
                    [$class: 'AmazonWebServicesCredentialsBinding',
                     credentialsId: 'aws-master-account']
                ]) {
                    bat 'python healthcheck.py'
                }
            }
        }
    }
}