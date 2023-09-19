#!/usr/bin/env python3
# coding: utf8

# default libraries
import logging
import re
from typing import Iterator, List, Union, Dict, Set, Iterable, Generator
from pathlib import Path

# local libraries
from ppanggolin.genome import Organism, Contig, Gene
from ppanggolin.region import Region, Spot, Module
from ppanggolin.geneFamily import GeneFamily
from ppanggolin.edge import Edge
from ppanggolin.metadata import Metadata


class Pangenome:
    """
    This is a class representing your pangenome. It is used as a basic unit for all the analysis to access to the
    different elements of your pangenome, such as organisms, contigs, genes or gene families. It has setter and getter
    methods for most elements in your pangenome, and you can use those to add new elements to it,
    or get objects that have a specific identifier to manipulate them directly.
    """

    def __init__(self):
        """Constructor method.
        """
        self.file = None

        # basic parameters
        self._famGetter = {}
        self._org_index = None
        self._fam_index = None
        self._max_fam_id = 0
        self._orgGetter = {}
        self._edgeGetter = {}
        self._regionGetter = {}
        self._spotGetter = {}
        self._moduleGetter = {}
        self.status = {
            'genomesAnnotated': "No",
            'geneSequences': "No",
            'genesClustered': "No",
            'defragmented': "No",
            'geneFamilySequences': "No",
            'neighborsGraph': "No",
            'partitioned': "No",
            'predictedRGP': "No",
            'spots': "No",
            'modules': 'No',
            "metadata": {"families": 'No',
                         "genes": 'No',
                         "genomes": 'No',
                         "RGPs": 'No',
                         "spots": 'No',
                         "modules": 'No'},
            "metasources": {"families": [],
                            "genes": [],
                            "genomes": [],
                            "RGPs": [],
                            "spots": [],
                            "modules": []}
        }
        self.parameters = {}

    def add_file(self, pangenome_file: Path):
        """Links an HDF5 file to the pangenome. If needed elements will be loaded from this file,
        and anything that is computed will be saved to this file when
        :func:`ppanggolin.formats.writeBinaries.writePangenome` is called.

        :param pangenome_file: A string representing filepath to hdf5 pangenome file to be either used or created

        :raises AssertionError: If the `pangenome_file` is not an instance of the Path class
        """
        assert isinstance(pangenome_file, Path), "pangenome file should be a Path object type"
        from ppanggolin.formats.readBinaries import get_status
        # importing on call instead of importing on top to avoid cross-reference problems.
        get_status(self, pangenome_file)
        self.file = pangenome_file.absolute().as_posix()

    """ Gene Methods"""
    @property
    def genes(self) -> Generator[Gene, None, None]:
        """Generator of genes in the pangenome.
        
        :return: gene generator
        """
        if self.number_of_organisms > 0:  # if we have organisms, they're supposed to have genes
            for org in self.organisms:
                for contig in org.contigs:
                    for gene in contig.genes:
                        yield gene
        elif self.number_of_gene_families > 0:
            # we might have no organism loaded, in that case there are gene families.
            for gene_fam in self.gene_families:
                for gene in gene_fam.genes:
                    yield gene
        else:
            logging.getLogger("PPanGGOLiN").warning("There is no gene in your pangenome")

    def _mk_gene_getter(self):
        """
        Builds the attribute _geneGetter of the pangenome

        Since the genes are never explicitly 'added' to a pangenome (but rather to a gene family, or a contig),
        the pangenome cannot directly extract a gene from a geneID since it does not 'know' them.
        If at some point we want to extract genes from a pangenome we'll create a geneGetter.
        The assumption behind this is that the pangenome has been filled and no more gene will be added.
        """
        self._geneGetter = {}
        for gene in self.genes:
            self._geneGetter[gene.ID] = gene

    def get_gene(self, gene_id: str) -> Gene:
        """Returns the gene that has the given gene ID

        :param gene_id: The gene ID to look for

        :return: Returns the gene that has the ID `gene_id`

        :raises AssertionError: If the `gene_id` is not an integer
        :raises KeyError: If the `gene_id` is not in the pangenome
        """
        assert isinstance(gene_id, str), "Gene id should be an integer"

        try:
            return self._geneGetter[gene_id]
        except AttributeError:
            # in that case, either the gene getter has not been computed, or the geneID is not in the pangenome.
            self._mk_gene_getter()  # make it
            return self.get_gene(gene_id)  # Return what was expected. If geneID does not exist it will raise an error.
        except KeyError:
            raise KeyError(f"{gene_id} does not exist in the pangenome.")

    @property
    def number_of_genes(self) -> int:
        """Returns the number of gene present in the pangenome

        :return: The number of genes
        """
        try:
            return len(self._geneGetter)
        except AttributeError:  # in that case the gene getter has not been computed
            self._mk_gene_getter()  # make it
            return len(self._geneGetter)

    """RNAs methods"""
    @property
    def RNAs(self) -> Generator[Gene, None, None]:
        """Generator of genes in the pangenome.

        :return: gene generator
        """
        for org in self.organisms:
            for contig in org.contigs:
                yield from contig.RNAs

    @property
    def number_of_rnas(self) -> int:
        """Returns the number of gene present in the pangenome

        :return: The number of genes
        """
        return sum(ctg.number_of_rnas for ctg in self.contigs)

    """Gene families methods"""
    @property
    def max_fam_id(self):
        """Get the last family identifier
        """
        return self._max_fam_id

    @max_fam_id.setter
    def max_fam_id(self, value):
        """Set the last family identifier

        :param value: value of the maximum family identifer
        """
        self._max_fam_id = value

    @property
    def gene_families(self) -> Generator[GeneFamily, None, None]:
        """Returns all the gene families in the pangenome
        
        :return: Generator of gene families
        """
        for family in self._famGetter.values():
            yield family

    @property
    def number_of_gene_families(self) -> int:
        """Returns the number of gene families present in the pangenome

        :return: The number of gene families
        """
        return len(self._famGetter)

    def get_gene_family(self, name: str) -> GeneFamily:
        """Returns the gene family that has the given `name`

        :param name: The gene family name to look for

        :return: Returns the gene family that has the name `name`

        :raises AssertionError: If the `name` is not an integer
        :raises KeyError: If the `name` is not corresponding to any family in the pangenome
        """
        assert isinstance(name, str), "Name of gene family should be a string"
        try:
            fam = self._famGetter[name]
        except KeyError:
            raise KeyError(f"Gene family with name={name} is not in pangenome")
        except Exception as error:
            raise Exception(error)
        else:
            return fam

    def add_gene_family(self, family: GeneFamily):
        """
        Get the :class:`ppanggolin.geneFamily.GeneFamily` object that has the given `name`.
        If it does not exist, creates it.

        :param family: The gene family to add in pangenomes

        :raises KeyError: Exception if family with the same name already in pangenome
        :raises Exception: Unexpected exception
        """
        try:
            _ = self.get_gene_family(family.name)
        except KeyError:
            self._famGetter[family.name] = family
            self.max_fam_id += 1
        except Exception as error:
            raise Exception(error)
        else:
            raise KeyError("Gene Family already exist")

    """Graph methods"""
    @property
    def edges(self) -> Generator[Edge, None, None]:
        """Returns all the edges in the pangenome graph
        
        :return: Generator of edge
        """
        for edge in self._edgeGetter.values():
            yield edge

    def add_edge(self, gene1: Gene, gene2: Gene) -> Edge:
        """
        Adds an edge between the two gene families that the two given genes belong to.

        :param gene1: The first gene
        :param gene2: The second gene

        :return: The created Edge

        :raises AssertionError: Genes object are expected
        :raises AttributeError: Genes are not associated to any families
        """
        assert isinstance(gene1, Gene) and isinstance(gene2, Gene), "Gene object are expected"
        try:
            family_1, family_2 = gene1.family, gene2.family
        except AttributeError:
            raise AttributeError("Genes are not linked to families. Check that you compute the gene families and post an"
                                 " issue on our GitHub")
        key = frozenset([family_1, family_2 ])
        edge = self._edgeGetter.get(key)
        if edge is None:
            edge = Edge(gene1, gene2)
            self._edgeGetter[key] = edge
        else:
            edge.add_genes(gene1, gene2)
        return edge

    @property
    def number_of_edges(self) -> int:
        """Returns the number of edge present in the pangenome

        :return: The number of gene families
        """
        return len(self._edgeGetter)

    """Organism methods"""
    @property
    def organisms(self) -> Generator[Organism, None, None]:
        """Returns all the organisms in the pangenome
        
        :return: Generator :class:`ppanggolin.genome.Organism`
        """
        for organism in self._orgGetter.values():
            yield organism

    @property
    def number_of_organisms(self) -> int:
        """Returns the number of organisms present in the pangenome
        
        :return: The number of organism
        """
        return len(self._orgGetter)

    @property
    def contigs(self) -> Generator[Contig, None, None]:
        for organism in self.organisms:
            yield from organism.contigs
    @property
    def number_of_contigs(self) -> int:
        """Returns the number of contigs present in the pangenome

        :return: The number of contigs
        """
        return sum(len(org) for org in self.organisms)

    def _mk_contig_getter(self):
        """
        Builds the attribute _contig_getter of the pangenome

        Since the genes are never explicitly 'added' to a pangenome (but rather to an organism),
        the pangenome cannot directly extract a gene from a geneID since it does not 'know' them.
        If at some point we want to extract contig from a pangenome we'll create a contig_getter.
        The assumption behind this is that the pangenome has been filled and no more contig will be added.
        """
        self._contig_getter = {}
        for contig in self.contigs:
            self._contig_getter[contig.name] = contig

    def get_contig(self, name: str) -> Contig:
        """Returns the contig that has the given name

        :param name: The ,ame of the contig to look for

        :return: Returns the wanted contig

        :raises AssertionError: If the `gene_id` is not an integer
        :raises KeyError: If the `gene_id` is not in the pangenome
        """
        assert isinstance(name, str), "Contig name should be a string"

        try:
            return self._contig_getter[name]
        except AttributeError:
            # in that case, either the gene getter has not been computed, or the geneID is not in the pangenome.
            self._mk_contig_getter()  # make it
            return self.get_contig(name)  # Return what was expected. If geneID does not exist it will raise an error.
        except KeyError:
            raise KeyError(f"Contig: {name}, does not exist in the pangenome.")
    def get_organism(self, name: str) -> Organism:
        """
        Get an organism that is expected to be in the pangenome using its name, which is supposedly unique.
        Raises an error if the organism does not exist.

        :param name: Name of the Organism to get

        :return: The related Organism object

		:raise AssertionError: If the organism name is not a string
        :raises KeyError: If the provided name is not an organism in the pangenome
        """
        assert isinstance(name, str), "Organism name should be a string"
        try:
            return self._orgGetter[name]
        except KeyError:
            raise KeyError(f"{name} does not seem to be in your pangenome")

    def add_organism(self, organism: Organism):
        """
        Adds an organism that did not exist previously in the pangenome if an Organism object is provided.
        If an organism with the same name exists it will raise an error.
        If a str object is provided, will return the corresponding organism that has this name
        OR create a new one if it does not exist.

        :param organism: Organism to add to the pangenome

        :raise AssertionError: If the organism name is not a string
        :raises KeyError: if the provided organism is already in pangenome
        """
        assert isinstance(organism, Organism), "An organism object is expected to be add to pangenome"
        try:
            self.get_organism(organism.name)
        except KeyError:
            self._orgGetter[organism.name] = organism
        else:
            raise KeyError(f"Redondant organism name was found ({organism.name})."
                           f"All of your organisms must have unique names.")

    def get_org_index(self) -> Dict[Organism, int]:  # will not make a new index if it exists already
        """Creates an index for Organisms (each organism is assigned an Integer).

        :return: The index of organisms in pangenome
        """
        if self._org_index is None:  # then the index does not exist yet
            self._org_index = {}
            for index, org in enumerate(self.organisms):
                self._org_index[org] = index
        return self._org_index

    def compute_family_bitarrays(self, part: str = 'all') -> Dict[Organism, int]:
        """
        Based on the index generated by get_org_index, generate a bitarray for each gene family.
        If the family j is present in the organism with the index i, the bit at position i will be 1. If it is not,
        the bit will be 0.
        The bitarrays are gmpy2.xmpz object.

        :param part: Filter the organism in function of the given partition

        :return: The index of organisms in pangenome
        """
        if self._org_index is None:
            # then the bitarrays don't exist yet, since the org index does not exist either.
            self.get_org_index()
        for fam in self.gene_families:
            fam.mk_bitarray(self._org_index, partition=part)
        # case where there is an index but the bitarrays have not been computed???
        return self._org_index

    def get_fam_index(self) -> Dict[GeneFamily, int]:  # will not make a new index if it exists already
        """Creates an index for gene families (each family is assigned an Integer).

        :return: The index of families in pangenome
        """
        if self._fam_index is None:  # then the index does not exist yet
            self._fam_index = {}
            for index, fam in enumerate(self.gene_families):
                self._fam_index[fam] = index
        return self._fam_index

    def compute_org_bitarrays(self, part='all') -> Dict[GeneFamily, int]:
        """
        Based on the index generated by get_fam_index, generate a bitarray for each gene family.
        If the family j is present in the organism with the index i, the bit at position i will be 1. If it is not,
        the bit will be 0.
        The bitarrays are gmpy2.xmpz object.

        :param part: Filter the organism in function of the given partition

        :return: The index of gene families in pangenome
        """
        if self._fam_index is None:
            # then the bitarrays don't exist yet, since the org index does not exist either.
            self.get_fam_index()
        for org in self.organisms:
            org.mk_bitarray(index=self._fam_index, partition=part)
        # case where there is an index but the bitarrays have not been computed???
        return self._fam_index

    """RGP methods"""
    @property
    def regions(self) -> Generator[Region, None, None]:
        """returns all the regions (RGP) in the pangenome

        :return: list of RGP
        """
        for region in self._regionGetter.values():
            yield region

    def get_region(self, name: str) -> Region:
        """Returns a region with the given region_name. Creates it if it does not exist.

        :param name: The name of the region to return

        :return: The region

        :raise AssertionError: If the RGP name is not a string
        :raises KeyError: If the provided name is not a RGP in the pangenome
        """
        assert isinstance(name, str), "RGP name should be a string"

        try:
            rgp = self._regionGetter[name]
        except KeyError:  # then the region is not stored in this pangenome.
            raise KeyError(f"There is no RGP with name={name}")
        else:
            return rgp

    def get_multigenics(self, dup_margin: float, persistent: bool = True) -> Set[GeneFamily]:
        """
        Returns the multigenic persistent families of the pangenome graph. A family will be considered multigenic
        if it is duplicated in more than `dup_margin` of the genomes where it is present.

        :param dup_margin: The ratio of presence in multicopy above which a gene family is considered multigenic
        :param persistent: if we consider only the persistent genes

        :return: Set of gene families considered multigenic
        """
        assert isinstance(dup_margin, float), "Dup margin should be a float"
        assert isinstance(persistent, bool), "persistent should be a boolean"

        multigenics = set()
        for fam in self.gene_families:
            if fam.named_partition == "persistent" or not persistent:
                dup = len([genes for org, genes in fam.get_org_dict().items() if
                           len([gene for gene in genes if not gene.is_fragment]) > 1])
                if (dup / fam.number_of_organisms) >= dup_margin:  # tot / nborgs >= 1.05
                    multigenics.add(fam)
        return multigenics

    def add_region(self, region: Region):
        """Add a region to the pangenome

        :param region: Region to add in pangenome

		:raise AssertionError: Error if region is not a Region object
        :raise KeyError: Error if another Region exist in pangenome with the same name
        """
        assert isinstance(region, Region), "A Region object is expected"

        try:
            self.get_region(region.name)
        except KeyError:
            self._regionGetter[region.name] = region
        else:
            raise KeyError(f"A RGP with this name ({region.name} already exist in pangenome")

    @property
    def number_of_rgp(self) -> int:
        """Returns the number of gene families present in the pangenome

        :return: The number of gene families
        """
        return len(self._regionGetter)

    """Spot methods"""
    @property
    def spots(self) -> Generator[Spot, None, None]:
        """Generate spots in the pangenome

        :return: Spot generator"""
        yield from self._spotGetter.values()

    def get_spot(self, spot_id: Union[int, str]) -> Spot:
        # TODO Change for only str or only int
        """
        Returns the spot that has the given spot ID.

        :param spot_id: The spot ID to look for. It can be an integer or a string in the format 'spot_<integer>'.

        :return: The spot with the specified ID.

        :raises KeyError: If the spot ID does not exist in the pangenome.
        :raises ValueError: If the provided spot ID does not have the expected format.
        """
        try:
            spot_id = int(spot_id)
        except ValueError:
            result = re.search(r"^spot_(\d+)$", spot_id)
            if result:
                spot_id = int(result.group(1))
            else:
                raise ValueError(f"The provided spot ID '{spot_id}' does not have the expected format."
                                 "It should be an integer or in the format 'spot_<integer>'.")
        try:
            spot = self._spotGetter[spot_id]
        except KeyError:
            raise KeyError(f"Spot {spot_id} does not exist in the pangenome.")
        else:
            return spot

    def add_spot(self, spot: Spot):
        """Adds the given iterable of spots to the pangenome.

        :param spot: Spot which should be added

        :raise AssertionError: Error if spot is not a Spot object
        :raise KeyError: Error if another Spot exist in pangenome with the same identifier
        """
        assert isinstance(spot, Spot), "Spot object is expected"
        try:
            self.get_spot(spot.ID)
        except KeyError:
            self._spotGetter[spot.ID] = spot
        except Exception as error:
            raise Exception(error)
        else:
            raise KeyError("Spot already exist")

    @property
    def number_of_spots(self) -> int:
        """Returns the number of gene families present in the pangenome

        :return: The number of gene families
        """
        return len(self._spotGetter)

    """Modules methods"""
    @property
    def modules(self) -> Generator[Module, None, None]:
        """Generate modules in the pangenome
        """
        yield from self._moduleGetter.values()

    def get_module(self, module_id: Union[int, str]) -> Module:
        # TODO Change for only str or only int
        """
        Returns the module that has the given module ID.

        :param module_id: The module ID to look for. It can be an integer or a string in the format 'module_<integer>'.

        :return: The module with the specified ID.

        :raises KeyError: If the module ID does not exist in the pangenome.
        :raises ValueError: If the provided module ID does not have the expected format.
        """

        try:
            module_id = int(module_id)
        except ValueError:
            result = re.search(r"^module_(\d+)$", module_id)
            if result:
                module_id = int(result.group(1))
            else:
                raise ValueError(f"The provided module ID '{module_id}' does not have the expected format."
                                 "It should be an integer or in the format 'module_<integer>'.")

        try:
            module = self._moduleGetter[module_id]
        except KeyError:
            raise KeyError(f"Module {module_id} does not exist in the pangenome.")
        else:
            return module

    def add_module(self, module: Module):
        """Add the given module to the pangenome

        :param module: Module to add in pangenome

        :raise AssertionError: Error if module is not a Module object
        :raise KeyError: Error if another module exist in pangenome with the same name
        """
        assert isinstance(module, Module), "Module object is expected"
        try:
            self.get_module(module.ID)
        except KeyError:
            self._moduleGetter[module.ID] = module
        except Exception as error:
            raise Exception(error)
        else:
            raise KeyError("Module already exist")

    def compute_mod_bitarrays(self, part: str = 'all') -> Dict[GeneFamily, int]:
        """Based on the index generated by get_fam_index, generated a bitarray
        for each gene family present in modules.
        If the family j is present in the module with the index i, the bit at position i will be 1. If it is not,
        the bit will be 0.
        The bitarrays are gmpy2.xmpz object.

        :param part: Filter the organism in function of the given partition

        :return: A dictionary with Organism as key and int as value.
        """
        if self._fam_index is None:
            # then the bitarrays don't exist yet, since the org index does not exist either.
            self.get_fam_index()
        for module in self.modules:
            module.mk_bitarray(index=self._fam_index, partition=part)
        # case where there is an index but the bitarrays have not been computed???
        return self._fam_index

    @property
    def number_of_modules(self) -> int:
        """Returns the number of modules present in the pangenome

        :return: The number of modules
        """
        return len(self._moduleGetter)

    """Metadata"""
    def select_elem(self, metatype: str):
        """Get all the element for the given metatype

        :param metatype: Name of pangenome component that will be get

        :return: All elements from pangenome for the metatype

		:raise AssertionError: Error if metatype is not a string
        :raise KeyError: Error if metatype is not recognized
        """
        assert isinstance(metatype, str), "Metatype name should be a string"

        if metatype == "families":
            return self.gene_families
        elif metatype == "genomes":
            return self.organisms
        elif metatype == "genes":
            return self.genes
        elif metatype == "RGPs":
            return self.regions
        elif metatype == "spots":
            return self.spots
        elif metatype == "modules":
            return self.modules
        else:
            raise KeyError("Given metatype is not allowed")

    def metadata_sources(self, metatype: str) -> Set[str]:
        """Returns all the metadata source in the pangenomes

        :param metatype: Select to which pangenome element metadata should be searched

        :return: Set of metadata source

        :raise AssertionError: Error if metatype is not a string
        """
        source_set = set()
        for elem in self.select_elem(metatype):
            for source_metadata in elem.sources:
                source_set.add(source_metadata)
        return source_set

    def metadata(self, metatype: str) -> Generator[Metadata, None, None]:
        """Create a generator with all metadatas in the pangenome

		:param metatype: Select to which pangenome element metadata should be generate

        :return: Set of metadata source
        """
        for elem in self.select_elem(metatype):
            yield elem.metadata

    def get_elem_by_metadata(self, metatype: str, **kwargs) -> Generator[
        Union[GeneFamily, Gene, Organism, Region, Spot, Module], None, None]:
        """Get element in pangenome with metadata attribute expected

        :param metatype: Select to which pangenome element metadata
        :param kwargs: attributes to identify metadata

        :return: Metadata element
        """
        for elem in self.select_elem(metatype):
            if len(list(elem.get_metadata_by_attribute(**kwargs))) > 0:
                yield elem

    def get_elem_by_sources(self, source: List[str], metatype: str) -> Generator[
        Union[GeneFamily, Gene, Organism, Region, Spot, Module], None, None]:
        """ Get gene famlies with a specific source in pangenome

        :param source: Name of the source

        :return: Gene families with the source
        """
        assert metatype in ["families", "genomes", "genes", "RGPs", "spots", "modules"]
        for elem in self.select_elem(metatype):
            if elem.get_metadata_by_source(source) is not None:
                yield elem
