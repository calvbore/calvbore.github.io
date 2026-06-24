---
title: Provable Data Origin, The Platapus Method, A Brief.
date: 2023-07-13
categories: hardware, protocols
---

*(Special thanks to [Daniel Kang](https://twitter.com/daniel_d_kang) for feedback on this article.)*

**P**rotocol for **L**ocation **A**nd **T**ime **A**ttested **P**henomena of **U**ser **S**ensor data. PLATAPUS. Because silly names are fun.

The platapus method will allow real world data creators to prove that data was captured within a defined time and location window. The method is constructed upon two key pillars. First, that a trusted attested sensor can be used to guarantee that data was produced after another piece of data. Second, that publishing a piece of data to a public network guarantees that the data was produced prior to the publication. 

If these two properties are upheld then we can provably create data within a time and location window.

## Programmable Attested Sensor
The method relies primarily on a piece of trusted hardware, an attested sensor. The proposed hardware is a sensor that can be preloaded with arbitrary data. The sensor produces the data captured from the world with a digital signature containing both the `captured data` and the `preloaded data`. Because the sensor is a trusted piece of hardware the signature assures that the captured data was produced after the preloaded data.

Let's define some terms for the rest of the article:
- `preloaded data`: arbitrary data that can be loaded into the sensor.
- `captured data`: the data captured by the sensor.
- `sensor signature`: a signature produced by the sensor, and included in the `captured data`'s metadata, assuring that the `captured data` was produced after the `preloaded data`.

```plantuml
component "trusted hardware" {
portin sensor
portin "data input" as di
portin "instruction input" as ii

[execution environment] as ee

portout output as out
}

[user device] as ud

[world] --> sensor: captured data
ud --> di: preloaded data
ud -->ii

sensor --> ee
di --> ee
ii --> ee
ee --> out

out --> () "captured data"
out --> () "metadata: incl. sensor signature"
```

Why must trusted hardware be used for this method?

A verifiable time window of the captured data would be impossible without trusted hardware. A software based solution seems trivial to exploit. Even with verifiable computation via a [zero knowledge](https://vitalik.ca/general/2021/01/26/snarks.html) [proof](https://www.risczero.com/), or private computation with [fully homomorphic encryption](https://6min.zama.ai/), the software could still be fed arbitrary `preloaded data` that may have been captured, or synthetically produced, at any time before or after what is supposed to be trusted `captured data`. There would be no guarantee that the data was captured by a sensor, or that the data was authentic, and produced after the `preloaded data`, breaking the method's time window guarantee. We must ensure that the `captured data` is produced after the `preloaded data` has been generated to preserve the properties of the method. A secure trusted hardware sensor seems the only way to ensure the method's goals.

## Time, Location, and Publishing Networks
The method will also require the use of a decentralized network to provide provable time and location claims. A network like [ethereum](https://ethereum.org/) could provide time claims for the opening of the method's time window and also feasibly be used as a data availability provider for publishing the captured data or sensor signature, as a means of closing the method's time window. 

The lack of location capabilities in ethereum would then point towards a network like [FOAM](https://foam.space/). FOAM is a network of distributed nodes providing location services via [LPWAN](https://medium.com/@dconrad/how-new-long-range-radios-will-change-the-internet-of-things-ed8e6b5e367f)(Low Power Wide Area Networks). When a user requests a presence claim from FOAM they broadcast a small message (about 100 bytes) to the network containing primarily of a [cryptographic signature](https://blog.foam.space/the-anatomy-of-a-zone-e8abc4ceca85).

```plantuml
participant sensor #orange
participant user #lightgreen
collections network #orange
user -> network: broadcast request
network -> user: return presence claim
user -> sensor: program presence claim watermark
sensor <- sensor: capture data
sensor -> user: retreive watermarked data
user -> network: publish data to network
network --> user: retreive data
user <- user: generate proof of inclusion
```

Using FOAM we could request a presence claim and use it as the `preloaded data` for our attested sensor. Then, request a second presence claim with the hash of the captured data (alternative parameters or signing methods could be used, options may be explored in a future article), this effectively publishes a hash of the `captured data` to the FOAM network. The two presence claims give us the openings and closings of the time and location window for the sensor data and are added to the metadata with a zk-proof assuring both claims have followed the protocol. 

There is not much to be done about withholding the data to be published/released at a later time. However, if the two presence claims are close to one another in both location and time (additionally, we could tie the signature of the second presence claim to the attested sensor that generated the `captured data`) we can be fairly sure of where and when the sensor data was captured, but as the time between presence claims increases the confidence in the location claim becomes weaker. Each application using the method will have to define some confidence interval between presence claims for its use case and if the data doesn't meet that definition it may dismiss it. As long as the attested sensor has not been compromised we can be sure that the data was produced between the two presence claims.

If location claims are not desired we could go ahead and use the latest ethereum blockhash as the `preloaded data`, and then publish the `sensor signature` into ethereum's blobspace.

Using a decentralized network is nice because we can use its trustless structure to prove things about data while using or authenticating it on-chain, without relying on an additional trusted party.

In practice a decentralized network could be substituted with a trusted authority that would provide signed attestations for either, or both, the opening and closing of the method's window. Publishing could also take place on a centralized service such as a social media provider or image host. However, introducing an additional centralized source (after the manufacturer of the trusted sensor) reduces the security and efficacy of the method. Composability is a property that cannot be understated, and so prioritising decentralized networks should be the preference of the method.

## Conclusion
The platapus method relies on two main properties. Firstly, trusted hardware can guarantee that digital data was produced after another piece of data. And secondly, publicly publishing data ensures that data was created prior to publication. An implementation of this method seems far away at this point in time (May 2023), but after the development of a programmable attested sensor, and the deployment of a widespread proof of location network like FOAM, this method could be used as a proof within standards like [C2PA](https://c2pa.org/) to authenticate the origin of data, and within  decentralized apps as verifiable real world data.