import React, { Component } from 'react';
import {
  Container,
  Row,
  Col,
  Jumbotron,
  Button
} from 'reactstrap';

import Client from '../client'
import Navigation from './Navigation'
import Settings from './Settings'
import Home from './Home'

import {
  BrowserRouter as Router,
  Route,
  Link,
  Switch
} from 'react-router-dom'

import uuid from 'uuid'

class Main extends Component {
  constructor(props) {
    super(props);

    this.toggle = this.toggle.bind(this);
    this.state = {
      isOpen: false,
      constituencies: [],
      parties: [],
      electionRules: {},
      simulationRules: {},
      presets: [],
      adjustmentMethods: {},
      dividerRules: {},
      votes: []
    };
  }
  
  toggle() {
    this.setState({
      isOpen: !this.state.isOpen
    });
  }

  componentDidMount() {
      Client.getCapabilities( (data) => {
          console.log("Found presets: ", data.presets);
          this.setState({
              adjustmentMethods: data.capabilities.adjustment_methods,
              dividerRules: data.capabilities.divider_rules,
              electionRules: data.election_rules,
              simulationRules: data.simulation_rules,
              presets: data.presets,
              errors: data.presets.filter(p => {if('error' in p) return p.error})
          })
      });
  }
  render() {
    console.log(this.state)
    return (
      <div>
        <Navigation props={this.state} />
        <Jumbotron>
          <Container>          
            <Route exact path='/' component={Home} />              
            <Route path='/settings' render={(props) => (
              <Settings
                electionRules={this.state.electionRules}
                adjustmentMethods={this.state.adjustmentMethods}
                dividerRules={this.state.dividerRules}
                {...props} />
            )} />

          </Container>
        </Jumbotron>
      </div>
    );
  }
}

export default Main;
