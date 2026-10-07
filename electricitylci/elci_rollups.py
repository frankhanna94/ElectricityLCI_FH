#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# elci_rollups.py
#
##############################################################################
# REQUIRED MODULES
##############################################################################
import os
import logging
import uuid
import pandas as pd
import datetime

import olca_schema as olca
import olca_schema.units as o_units

import netlolca

##############################################################################
# MODULE DOCUMENTATION
##############################################################################
__doc__ = """
Utilities for rolling up legacy Electricity Life Cycle Inventory (eLCI)
configurations.

This module provides methods to streamline the processing and roll-up of
older eLCI configurations, such as the 2016 electricity baseline. The
workflow is intended to be performed as a post-processing step after the
corresponding JSON-LD package has been imported into a new openLCA database.

The general workflow is:

1. Import the legacy eLCI JSON-LD package into a new openLCA database.
2. Connect to the openLCA database.
3. Roll up selected processes:
   * Roll up all applicable processes, or
   * Roll up only consumption mix processes, based on user input.

   Consumption mix process UUIDs are preserved across eLCI versions and can
   therefore be used to identify these processes when a consumption-mix-only
   roll-up is requested.
4. Rename the newly created system processes by appending the corresponding
   eLCI year.
5. Remove the original unit processes and product systems, leaving only the
   newly generated system processes.

The main routine coordinates the workflow by iterating through the selected
processes, calling the existing N-CLAD roll-up functionality, renaming the
resulting system processes, and removing obsolete database objects.

Notes
-----
This module assumes that the legacy JSON-LD package has already been imported
into a dedicated openLCA database before execution. Process roll-up functionality
is provided by the corresponding helper utilities in the N-CLAD source code.
"""

##############################################################################
# GLOBALS
##############################################################################
consumption_mix_processes = [
    "75d4be66-12a7-30b3-bc57-fa724c941b0e",
    "820dce70-1ea5-3b8a-b551-e8660e280f9f",
    "37733d38-be37-32eb-a6ad-4f119294136f",
    "9f6a16c6-3df8-39f0-8b4e-af72c0e663ca",
    "a2522eb7-a557-3242-8d26-042fc4b41195",
    "8aaa2df9-e6e6-3774-91a1-553bed6a719a",
    "696cf4c2-3b38-37c2-81dc-187b767b4a1e",
    "11b43f23-fa67-3d22-9e80-8951c69d7b5e",
    "13ef9dff-c849-324e-a964-25fe48907c8c",
    "b16ca0d0-3f5c-3a24-a398-3bda3ffe06bd",
    "1744d0a0-5348-316f-ae28-9543f3a03d1d",
    "cc2dd726-d99f-3914-9c02-65b0ae57102a",
    "f268f3ff-e1c6-303b-b7f2-7290cc7b98d6",
    "72c31c1e-ae3f-32a3-89a9-8066379d5b3b",
    "c3557d8e-c91a-3e9c-bb90-47fe970a00ec",
    "46535c58-2c1d-3561-a5bb-a008b9c959d8",
    "c69563ec-887a-35ca-acc5-820ae0ba5f72",
    "337fc42a-81b5-3d8b-b98f-614d417bc11f",
    "dc255d13-6512-372d-8738-48739679d529",
    "34b70fb7-6d4a-3eae-99dc-9a3b4b4624df",
    "5c230c62-5c0e-36d5-bc0a-1e4d28ef30ab",
    "b9454a38-b53a-3d40-b121-058f233f9643",
    "5fbe46bd-265a-3a59-98fe-c74a1c223877",
    "690d5f79-401d-3d30-9eb3-944df1715f75",
    "7bd56448-965a-3e54-bf7f-f28608f4fe7a",
    "afb0a8ed-7e33-37ec-aa70-2286f8f84935",
    "9e5f30e4-76b0-307d-b75b-429fe18bb4e1",
    "f03e070d-463f-3d2f-82aa-b5bffa1cabd8",
    "6868698b-57f5-3ae2-bbb1-f3b160ef9945",
    "b683482f-bae9-3b2f-a7c8-ed8964094c04",
    "99661c17-082b-33a2-8d0e-8331d19831e2",
    "2789aa03-b05c-3374-9aaa-12d1a20a6a55",
    "4537d7cd-1dbf-37b5-a4c6-1a1f2c19a1de",
    "81511323-42bf-3f8e-9c9d-31d6d50e935d",
    "610df26a-4b74-30c3-be75-7af4e6021ab9",
    "ada5f6f3-eba8-35da-9ec4-df88c836ab68",
    "4502179f-467b-3952-b284-863fecbd2acb",
    "5b2599cc-deb4-3602-a484-1af00f05d770",
    "11b087d8-8981-373b-aef7-43a4a17cbe8e",
    "d640a8aa-93b2-3d0e-8012-24b79ead9694",
    "f80d17d0-8756-3933-9b8f-67f55495b5db",
    "73cf723e-ab4a-3ae1-9a1e-a34364cea714",
    "653d2bf8-9ace-33fd-a537-7b10dd2499c0",
    "026104f5-0d33-34d3-acf3-d92e6035156f",
    "22bf4ba1-b400-3ba2-bc0a-184a44694cc5",
    "81320fab-eef5-39b4-bf21-7cc2edb539c9",
    "64ddc11d-3d2b-3e2b-8c21-5fc1d11febfd",
    "3862d7de-4942-35b6-bf7b-6dc22ea6305f",
    "82651099-95cb-3377-b030-045e4cbed506",
    "f791afbb-cde3-3964-95f8-1865271d97c0",
    "688bedec-5571-3280-828d-4245f2b06f47",
    "85c361e4-4861-38d7-9441-accd93f4cfad",
    "98b00934-c348-3833-a480-7100e153e41e",
    "27e90eb9-c0a9-3c43-9f9c-839b703670c3",
    "ec6a9894-9221-34d6-9814-b0179435bac8",
    "64b4786b-0d0e-3f41-b49f-d51486884c98",
    "f41111d1-1668-325a-abd2-a40af161e35d",
    "9aa4d22e-c29e-35ac-b81d-1908de7be42b",
    "b42ca74f-a649-32d5-9a9f-6a9846e7af51",
    "231ed52a-5ec4-3216-9f16-3cbf4a7bb794",
    "db0fc1d8-d8ca-3875-8058-f9b4b4d01ac5",
    "91ba7e39-5ec0-3f25-b643-6b36dfd084b6",
    "f4ced9c2-776a-3137-9f04-af771f34cb8c",
    "5ac61f8b-20d0-3a99-a4a0-c888d8d23423",
    "1eba69d4-62c4-3a1b-ba13-d7f2893c1f28",
    "4a1816ca-5263-383b-bfbe-beec1acbb9c2",
    "c3096d7d-a9c4-3a39-9814-65304089d770",
    "476cb9dd-c521-3a06-8d12-c6cf472c0be1",
    "3d4710d5-b80d-38ca-b381-fd2125b0f542",
    "46626051-54c2-3142-9577-355822757d80",
    "3b623b7e-b22b-3903-9670-7aaac965357d",
    "5c13cc4e-b1eb-3fca-a291-b2891bd253a0",
    "ccbab212-154f-3421-b714-c24346bece5b",
    "f21316ee-5206-3cb6-80ac-9516cfd74abf",
    "f6579b75-679d-38ed-b7b8-e5026887b008",
    "6ea4ba30-2cef-3a68-99d7-efb3a2088e06",
    "483aa8c9-12d2-3a42-91f1-09085f3c9c6b",
    "081c824a-a8a4-3958-8e6e-1bf18e1841f2",
    "39a94f2a-03f7-38ca-9cf1-71a839287487",
    "668f4318-8e2e-35f1-82ab-4647e7bd42a8",
    "996438f6-ff4b-3c11-a44a-cc64ce7a7b30",
    "0082cc36-0aa6-3ff2-acf5-a2765411b57a",
    "0f3c15c4-b592-37c8-89c1-cace88810e03",
    "20dbe919-4e53-3360-a0d1-246de37e748d",
    "2ef4fd99-1137-3f5d-b3d6-fbe1930b2d7d",
    "163650de-0ebd-3f9b-b7f0-338701161e8b",
    "cab7d877-234b-3e69-8b8e-240cb7196021",
    "a9420547-6281-38fe-bb48-a32546ed849f",
    "79ea9941-224c-30bd-969d-4032cfaa8005",
    "d0481c35-49ba-3f00-9213-1b087ac9198e",
    "e06c46bf-e2d6-33bf-90e7-1f90eeb98dcb",
    "c06b0df8-1d75-39c6-aa87-49100c889658",
    "b74ffbc4-0dab-3f84-977f-531e3c5008c4",
    "9ce1f4d7-caf4-3f29-9208-b54a3803b295",
    "00f828c8-2aa5-3e86-a2cd-fabe0489d245",
    "ec5c89b7-509e-3fd7-9308-f51554c1b529",
    "ef86245c-837b-3555-b556-d1f5346f2f76",
    "1cca2393-ee00-3fa3-9884-986d39730113",
    "db2921f6-74d4-3e2f-9524-417d2e19c826",
    "6c24ac2c-dd77-3dff-a8cc-90054528ec3f",
    "7cbef411-51cd-3d49-bee8-49fdc4ef98cf",
    "a32b02de-c81f-3fba-bb48-58f5f5d9c2c8",
    "6334c6ab-2295-313a-8cbd-a8e86e846232",
    "07802327-0d38-3d14-a4b0-c71554da61d4",
    "7faaf99b-7a36-3c72-a485-dde4df9fd525",
    "02e2f5b0-74ac-3c4b-a691-d7b1ad5e3646",
    "9f160965-7cd6-3f2a-be2f-30e99e8d9696",
    "afd157a1-c37c-3f33-bd41-227114c381f8",
    "a9eed0a6-6813-3083-881a-ce9f6856fe0f",
    "3aed3164-bbec-3d54-a483-508a7765a9fd",
    "fdf79353-fbd3-30b4-aa15-267a212b9da4",
    "4a9358dd-5c89-3164-a6c0-40e40f587350",
    "1ea0668d-d780-3a6a-a4bc-3447358060df",
    "39890793-d56a-3616-9da0-be3a79f81aff",
    "73d35f2d-1256-3d90-b387-e6cd92f1b9b0",
    "018019c9-b57c-3bc7-ae20-4fcb66243960",
    "40ea324d-0b17-3f38-babd-6c1d93b99e3d",
    "b62e0b13-f036-3b07-aa74-c36a6c505d1a",
    "37b87ceb-2e31-3d38-baaa-84f148287d2f",
    "d29a1cb4-f929-3f9d-8aee-045fdae8cab4",
    "52249d0b-6d45-3f74-87fd-e62d8ddf000a",
    "112d97d5-63cb-324a-9413-6e64d2a6694b",
    "5739eaff-4c35-359d-8a18-cbc9149bde83",
    "dd3b1db6-c80a-3cc6-af99-237ef7f04606",
    "6ddae3ea-187e-3c07-9e17-29a65a5927a7",
    "ff87ed0b-db00-312a-bca8-2b9f2d3b3456",
    "ba6c7a86-9e38-357a-a11b-6fd0945a2e5e",
    "cd9c001f-0160-3ae9-82a5-81decd6beb4f",
    "d1e20ef2-31c8-3305-969a-e008341a50e1",
    "739a9cbd-7189-3c4b-ae7b-8b756e99bcfb",
    "a2a22977-2b95-358b-90ca-ca7f1fbeb167",
    "28382a88-b2b2-3cfe-985e-659290858e70",
    "75f0af0b-abe3-36f4-ae05-2fdf13c7167b",
    "3b36f413-39cb-3dc2-b513-fd2b1b4149c1",
    "b55ec9c6-062f-3cd6-aee0-940f3c589726",
    "6f718d2f-46c4-362a-a196-c261265ee736",
    "33c05d14-fa45-3b60-bef8-768168b22db9",
    "e4fcd21b-a651-31c8-a123-ff308a80e080",
    "0033b245-c828-3fe4-ba32-1e35bc4d30ca",
    "b47455f1-fc68-33b2-a2a8-217485ef8bba",
    "763f16bd-1c1e-336a-acc0-626123547161",
    "75132c61-a7bd-3cf4-a377-1e97e124becd",
]

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), ".netl_dd")
"""str : The hidden output folder in the user's home directory."""

QA_UNIT_CSV = os.path.join(OUTPUT_DIR, "qa_missing_units.csv")
"""str : The CSV file path for tracking missing units."""

##############################################################################
# MAIN FUNCTIONS
##############################################################################


def run_rollup_electricitylci(
    client, date=None, rollup_consumption_only=True, impact_method_uuid=None
):
    """
    Run the rollup of electricity LCI processes in an openLCA database.

    Parameters:
    - client: An instance of the openLCA client to connect to the database.
    - date: The date to append to the new name of the rolled up process.
    - rollup_consumption_only: A boolean indicating whether to roll up only
    consumption mix processes (True) or all processes (False).

    Returns:
    None
    """
    if date is None:
        logging.warning(
            "No date provided for rollup. "
            "The rolled up processes will not have a date appended to their names."
        )

    if impact_method_uuid is None:
        logging.warning(
            "No impact method UUID provided. "
            "Impact values will not be compared between original and rolled up processes."
        )

    # Step 1: Get list of processes and product systems uuids
    original_processes = client.get_spec_ids(olca.Process)
    original_product_systems = client.get_spec_ids(olca.ProductSystem)

    # Step 2: Rollup processes based on user input
    if rollup_consumption_only:
        # Roll up only consumption mix processes
        logging.info("Rolling up only consumption mix processes...")
        rollup_consumption_mix_processes(
            client, date, impact_method_uuid, new_name=None
        )
    else:
        # Roll up all processes
        logging.info("Rolling up all processes...")
        rollup_all_processes(
            client, original_processes, date, impact_method_uuid, new_name=None
        )

    # Step 3: Delete old processes
    for process in original_processes:
        delete_process(client, process)

    # Step 4: Delete all product systems
    for ps in original_product_systems:
        client.delete_product_system(ps)

    return


def rollup_consumption_mix_processes(client, date, impact_method_uuid, new_name):
    """
    Roll up only the consumption mix processes in the openLCA database.

    Parameters:
    - client: An instance of the openLCA client to connect to the database.
    - date: The date to append to the new name of the rolled up process.

    Returns:
    None
    """
    # Implementation for rolling up consumption mix processes
    for process_uuid in consumption_mix_processes:
        client.roll_up_process(
            process_uuid,
            date,
            prov_linking="only_defaults",
            impact_method_uuid=impact_method_uuid,
            new_name=new_name,
        )
    return None


def rollup_all_processes(client, process_uuids, date, impact_method_uuid, new_name):
    """
    Roll up all processes in the openLCA database.

    Parameters:
    - client: An instance of the openLCA client to connect to the database.
    - process_uuids: A list of UUIDs of the processes to be rolled up.
    - date: The date to append to the new name of the rolled up process.

    Returns:
    None
    """
    # Implementation for rolling up all processes
    for process_uuid in process_uuids:
        client.roll_up_process(
            process_uuid,
            date,
            prov_linking="only_defaults",
            impact_method_uuid=impact_method_uuid,
            new_name=new_name,
        )
    return None


def delete_process(client, process_uuid):
    """Helper function to delete a process"""
    pref = client.query(olca.Process, process_uuid).to_ref()
    client.client.delete(pref)
    return True
